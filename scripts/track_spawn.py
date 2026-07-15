#!/usr/bin/env python3
"""PostToolUse tracker on Agent|Task|Workflow: log WHICH role/model was
spawned, so the calibration phase has per-role delegation rates instead of
guard events only. Events, never prompt content.

Logged per spawn: role (subagent_type), explicit model override if the chair
set one (should stay empty — roles own their routing), background flag,
delegation size bucket (same measure as the spawn guard), and whether the
tool call errored.

Opt-in like the guards: silent outside dirigent sessions.
Summary: python3 scripts/stats.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirigent_common import read_payload, guards_enabled, delegation_chars, metric

TRACKED_TOOLS = {"Agent", "Task", "Workflow"}
KNOWN_ROLES = {"scout", "mech", "coder", "judge", "esc", "sec",
               "plan-check", "check", "check-max", "fork"}


def bucket(n: int) -> str:
    if n <= 500:
        return "<=500"
    if n <= 1500:
        return "<=1500"
    if n <= 5000:
        return "<=5000"
    return ">5000"


def main() -> int:
    payload = read_payload()
    if payload.get("tool_name") not in TRACKED_TOOLS:
        return 0
    if not guards_enabled(payload):
        return 0

    ti = payload.get("tool_input") or {}
    resp = payload.get("tool_response")
    role = str(ti.get("subagent_type") or "").strip() or "(default)"

    metric(
        "spawn",
        role=role,
        known=role.split(":")[-1] in KNOWN_ROLES,  # plugin agents arrive namespaced
        model_override=str(ti.get("model") or ""),  # should be "" — roles own routing
        background=bool(ti.get("run_in_background")),
        chars=bucket(delegation_chars(ti)),
        errored=bool(isinstance(resp, dict) and resp.get("is_error")),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
