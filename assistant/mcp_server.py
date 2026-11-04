#!/usr/bin/env python3
"""Host-side MCP tools for inspecting and managing this repository's Vagrant VM."""

import csv
import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    Resolve,
)
from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = "devstack-vm"
STATUS_TIMEOUT_SECONDS = 30
OPERATION_LOG_LIMIT = 6000
STATE_DIR = REPO_ROOT / ".devstack-mcp"
OPERATIONS_DIR = STATE_DIR / "operations"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devstack_mcp")
mcp = MCPServer("devstack-setup")


@dataclass
class Operation:
    process: subprocess.Popen
    action: str
    log_path: Path
    started_at: str


OPERATIONS: dict[str, Operation] = {}
OPERATIONS_LOCK = threading.Lock()


def vagrant_path() -> str:
    configured = os.environ.get("VAGRANT_BINARY", "vagrant")
    path = shutil.which(configured)
    if not path:
        raise RuntimeError("Vagrant executable not found. Install Vagrant or set VAGRANT_BINARY.")
    return path


def vagrant(args: list[str], timeout: int = STATUS_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    return subprocess.run(
        [vagrant_path(), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def instance_state() -> str:
    result = vagrant(["status", TARGET, "--machine-readable"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError("Could not read Vagrant state: {}".format(detail[-2000:]))
    for record in csv.reader(result.stdout.splitlines()):
        if len(record) >= 4 and record[2] == "state":
            return record[3]
    raise RuntimeError("Vagrant did not report a state for {}.".format(TARGET))


def get_status() -> dict[str, Any]:
    state = instance_state()
    response: dict[str, Any] = {
        "instance": TARGET,
        "instance_state": state,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if state != "running":
        response["services"] = None
        response["message"] = "Start the instance before requesting its in-guest service report."
        return response

    result = vagrant(["ssh", TARGET, "-c", "devstack-status --json"])
    try:
        service_report = json.loads(result.stdout)
    except json.JSONDecodeError:
        response["services"] = None
        response["status_command_error"] = (result.stderr or result.stdout).strip()[-2000:]
        response["message"] = (
            "The VM is running, but devstack-status did not return JSON. "
            "Provision the VM or inspect the command output."
        )
        return response

    response["services"] = service_report
    response["status_command_exit_code"] = result.returncode
    return response


def launch_operation(action: str, args: list[str]) -> dict[str, str]:
    with OPERATIONS_LOCK:
        for running_id, running_operation in OPERATIONS.items():
            if running_operation.process.poll() is None:
                raise RuntimeError(
                    "Cannot start {} while {} operation {} is still running.".format(
                        action, running_operation.action, running_id
                    )
                )

        OPERATIONS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            OPERATIONS_DIR.chmod(0o700)
        except OSError:
            logger.warning("Could not restrict permissions on %s", OPERATIONS_DIR)
        operation_id = str(uuid.uuid4())
        log_path = OPERATIONS_DIR / (operation_id + ".log")
        log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            with os.fdopen(log_fd, "w", encoding="utf-8") as output:
                process = subprocess.Popen(
                    [vagrant_path(), *args],
                    cwd=REPO_ROOT,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    text=True,
                )
        except Exception:
            log_path.unlink(missing_ok=True)
            raise

        operation = Operation(process, action, log_path, started_at)
        OPERATIONS[operation_id] = operation
    return {
        "operation_id": operation_id,
        "action": action,
        "instance": TARGET,
        "state": "running",
        "started_at": started_at,
        "log_file": str(log_path),
        "next_step": "Call get_devstack_operation_status with this operation_id to check progress.",
    }


def operation_status(operation_id: str) -> dict[str, Any]:
    try:
        parsed_id = str(uuid.UUID(operation_id))
    except ValueError as error:
        raise ValueError("operation_id must be a UUID returned by a lifecycle tool") from error
    with OPERATIONS_LOCK:
        operation = OPERATIONS.get(parsed_id)
    if operation is None:
        return {
            "operation_id": parsed_id,
            "state": "unknown",
            "message": "This MCP server does not have this operation in its current session.",
        }

    return_code = operation.process.poll()
    state = "running" if return_code is None else ("succeeded" if return_code == 0 else "failed")
    try:
        with operation.log_path.open(encoding="utf-8", errors="replace") as log:
            log.seek(max(0, operation.log_path.stat().st_size - OPERATION_LOG_LIMIT))
            output_tail = log.read()
    except OSError:
        output_tail = "Operation log is unavailable."
    return {
        "operation_id": parsed_id,
        "action": operation.action,
        "instance": TARGET,
        "state": state,
        "started_at": operation.started_at,
        "return_code": return_code,
        "log_tail": output_tail,
        "log_file": str(operation.log_path),
    }


@mcp.tool()
def get_devstack_status() -> dict[str, Any]:
    """Return Vagrant instance state and, when running, the DevStack service report."""
    return get_status()


@mcp.tool()
def get_devstack_operation_status(operation_id: str) -> dict[str, Any]:
    """Check progress and recent output for a start or destroy operation."""
    return operation_status(operation_id)


@mcp.tool()
def start_devstack_instance() -> dict[str, str]:
    """Start or provision this repository's devstack-vm in the background."""
    state = instance_state()
    if state == "running":
        return {
            "instance": TARGET,
            "state": "already_running",
            "message": "The VM is already running. Use get_devstack_status to inspect DevStack services.",
        }
    return launch_operation("start", ["up", TARGET])


class DestroyConfirmation(BaseModel):
    confirm: bool


async def request_destroy_confirmation() -> DestroyConfirmation | Elicit[DestroyConfirmation]:
    return Elicit(
        "Permanently destroy the Vagrant VM devstack-vm and delete its VM disk? "
        "This cannot be undone. Confirm only if you want this instance and its data removed.",
        DestroyConfirmation,
    )


if os.environ.get("DEVSTACK_MCP_ENABLE_DESTROY") == "1":

    @mcp.tool()
    async def destroy_devstack_instance(
        confirmation: Annotated[
            ElicitationResult[DestroyConfirmation],
            Resolve(request_destroy_confirmation),
        ],
    ) -> dict[str, str]:
        """Destroy devstack-vm after asking the connected MCP host for direct user confirmation."""
        match confirmation:
            case AcceptedElicitation(data=DestroyConfirmation(confirm=True)):
                pass
            case AcceptedElicitation():
                return {"instance": TARGET, "state": "cancelled", "message": "VM was not destroyed."}
            case DeclinedElicitation() | CancelledElicitation():
                return {"instance": TARGET, "state": "cancelled", "message": "VM was not destroyed."}

        state = instance_state()
        if state == "not_created":
            return {"instance": TARGET, "state": "not_created", "message": "There is no VM to destroy."}
        return launch_operation("destroy", ["destroy", TARGET, "--force"])


if __name__ == "__main__":
    mcp.run()
