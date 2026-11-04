#!/usr/bin/env python3
"""Report the state of expected DevStack systemd units."""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from diagnose import suggestion


DEFAULT_CONFIG = Path("/etc/devstack-status/expected_services.json")


def run(command):
    return subprocess.run(command, text=True, capture_output=True, check=False)


def read_unit(unit):
    result = run([
        "systemctl", "show", unit,
        "--property=LoadState,ActiveState,SubState,Result,ExecMainStatus",
        "--no-pager",
    ])
    if result.returncode != 0:
        return {"load": "unknown", "active": "unknown", "sub": "unknown", "result": "unknown", "exit_code": "unknown"}
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    return {
        "load": values.get("LoadState", "unknown"),
        "active": values.get("ActiveState", "unknown"),
        "sub": values.get("SubState", "unknown"),
        "result": values.get("Result", "unknown"),
        "exit_code": values.get("ExecMainStatus", "unknown"),
    }


def journal_tail(unit, lines):
    command = ["journalctl", "--no-pager", "--unit", unit, "-n", str(lines)]
    result = run(command)
    if result.returncode != 0 and shutil.which("sudo"):
        result = run(["sudo", "-n", *command])
    return result.stdout.strip() if result.returncode == 0 else "Journal is unavailable to this user. Try: sudo journalctl -u {} -n {} --no-pager".format(unit, lines)


def load_services(path):
    with path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    services = config.get("services")
    if not isinstance(services, list) or not services:
        raise ValueError("configuration must contain a non-empty 'services' list")
    for entry in services:
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("unit"):
            raise ValueError("each service must have a name and unit")
    return services


def main():
    parser = argparse.ArgumentParser(description="Check the configured DevStack systemd services.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="service inventory JSON file")
    parser.add_argument("--journal-lines", type=int, default=12, help="journal lines to show for each unhealthy service")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    if args.journal_lines < 0:
        parser.error("--journal-lines must be zero or greater")
    if not shutil.which("systemctl"):
        print("ERROR: systemctl was not found; this command must run inside the DevStack VM.", file=sys.stderr)
        return 2

    try:
        services = load_services(args.config)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("ERROR: cannot load service inventory: {}".format(error), file=sys.stderr)
        return 2

    report = []
    for service in services:
        state = read_unit(service["unit"])
        if state["load"] == "not-found":
            status = "NOT FOUND"
        elif state["active"] == "active":
            status = "RUNNING"
        elif state["active"] == "failed":
            status = "FAILED"
        elif state["active"] in ("inactive", "deactivating"):
            status = "NOT RUNNING"
        else:
            status = "UNKNOWN"
        item = {"name": service["name"], "unit": service["unit"], "status": status, **state}
        if status != "RUNNING" and args.journal_lines:
            item["journal"] = journal_tail(service["unit"], args.journal_lines)
        item["suggestion"] = suggestion(status, {**state, "unit": service["unit"]}, item.get("journal", ""))
        report.append(item)

    unhealthy = [item for item in report if item["status"] != "RUNNING"]
    overall = "HEALTHY" if not unhealthy else "DEGRADED"
    if args.json:
        print(json.dumps({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "overall": overall,
            "services": report,
        }, indent=2))
    else:
        print("DevStack status: {}".format(overall))
        print("Checked at: {} UTC\n".format(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
        for item in report:
            print("{:<11} {:<24} {} ({}, {})".format(
                item["status"], item["name"], item["unit"], item["active"], item["sub"]
            ))
            if item["status"] != "RUNNING":
                print("  Next step: " + item["suggestion"])
            if item.get("journal"):
                print("  Recent journal:")
                for line in item["journal"].splitlines():
                    print("    " + line)
                print("  Inspect: sudo journalctl -u {} -n 100 --no-pager".format(item["unit"]))
        if unhealthy:
            print("\n{} configured service(s) are not confirmed running.".format(len(unhealthy)))
            print("This report checks systemd state; it does not prove each service API is responding.")
        else:
            print("\nAll configured service units are active.")
            print("This report checks systemd state; it does not prove each service API is responding.")
    return 1 if unhealthy else 0


if __name__ == "__main__":
    sys.exit(main())
