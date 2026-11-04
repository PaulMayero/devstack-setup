"""Conservative, local next-step guidance for DevStack unit states."""


def suggestion(status, state, journal):
    text = journal.lower()
    if status == "RUNNING":
        return "Systemd reports this unit active. Check its API separately if requests are failing."
    if status == "NOT FOUND":
        return "Verify this unit name against the installed DevStack version and confirm the service is enabled in local.conf."
    if status == "UNKNOWN":
        return "The unit state could not be determined. Run systemctl status for this unit and check systemd access."
    if "connection refused" in text or "connectionerror" in text:
        return "The log reports a connection failure. Check the named dependency's service and endpoint, then inspect this unit's journal again."
    if "no space left on device" in text:
        return "The log reports insufficient disk space. Check df -h and free space before restarting the service."
    if "permission denied" in text:
        return "The log reports a permission error. Check the referenced path's owner and permissions before restarting."
    if status == "FAILED":
        return "Read the first error in this unit's journal, resolve that cause, then restart only this unit with systemctl restart {}.".format(state.get("unit", "<unit>"))
    return "The unit is inactive. Confirm stack.sh completed and that this service is enabled; if it should be running, inspect its journal before starting it."
