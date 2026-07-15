#!/usr/bin/env python3
"""PreToolUse guard on Agent|Task|Workflow: deny spawning a chair (fab/ops)
as a subagent, and deny long delegations without a Requirements Ledger.
Exit 0 = pass, exit 2 = deny (stderr goes to Claude).

Opt-in: silent unless the session runs a dirigent chair, a ./.workflow dir
exists, or DIRIGENT_GUARDS=1. Short spawns (<= DIRIGENT_THRESHOLD chars
across prompt/script/description/args, default 1500) and forks always pass
the ledger gate; the chair gate has no size exemption.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirigent_common import (read_payload, guards_enabled, find_ledger,
                             delegation_chars, tool_input_dict, metric, CHAIRS)

GUARDED_TOOLS = {"Agent", "Task", "Workflow"}


def main() -> int:
    payload = read_payload()
    if payload.get("tool_name") not in GUARDED_TOOLS:
        return 0
    if not guards_enabled(payload):
        return 0

    ti = tool_input_dict(payload)

    sub = str(ti.get("subagent_type") or "").strip()
    if sub.split(":")[-1].strip().lower() in CHAIRS:
        metric("spawn_deny", reason="chair")
        sys.stderr.write(
            f"dirigent spawn guard: '{sub}' is a session chair, not a "
            "subagent — never delegate to it. Route the work to a worker "
            "role (scout/mech/coder/judge), escalate via esc, or verify "
            "via check/check-max.\n"
        )
        return 2

    chars = delegation_chars(ti)
    try:
        threshold = int(os.environ.get("DIRIGENT_THRESHOLD", "1500"))
    except ValueError:
        threshold = 1500

    if chars <= threshold:
        metric("spawn_pass", reason="short", chars=chars)
        return 0
    if sub.lower() == "fork":
        metric("spawn_pass", reason="fork", chars=chars)
        return 0
    if find_ledger(payload) is not None:
        metric("spawn_pass", reason="ledger", chars=chars)
        return 0

    metric("spawn_deny", chars=chars)
    sys.stderr.write(
        "dirigent spawn guard: this delegation is detailed ("
        f"{chars} chars > {threshold}) but ./.workflow/LEDGER.md does not "
        "exist. Write the Requirements Ledger first (one checkbox line per "
        "requirement/constraint/edge case) and cite its items in each spawn — "
        "or, if the task is genuinely small, do it yourself in the chair.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
