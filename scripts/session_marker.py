#!/usr/bin/env python3
"""SessionStart hook: record a per-session marker (started timestamp + chair).

The stop guard uses `started` to decide ledger ownership; the opt-in gate
uses `chair`. Re-fires on resume/clear/compact — the original `started`
timestamp is preserved.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirigent_common import read_payload, load_marker, save_marker, metric, CHAIRS


def detect_chair(payload: dict) -> str:
    for key in ("agent", "agent_name", "agent_type"):
        val = str(payload.get(key) or "").strip()
        name = val.split(":")[-1]  # plugin agents arrive namespaced: dirigent:fab
        if name in CHAIRS:
            return name
    return ""


def main() -> int:
    payload = read_payload()
    sid = payload.get("session_id", "")
    marker = load_marker(sid)
    if "started" not in marker:
        marker["started"] = time.time()
    chair = detect_chair(payload)
    if chair:
        marker["chair"] = chair
    save_marker(sid, marker)
    metric("session_start", chair=marker.get("chair", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
