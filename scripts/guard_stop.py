#!/usr/bin/env python3
"""Stop guard: block the session's close once while ledger items are open.

Exit 0 = pass, exit 2 = block (stderr goes to Claude). Passes when: guards
disabled, the stop already follows a blocked stop (`stop_hook_active` —
blocking again would loop), no ledger, every item closed/deferred, the
ledger predates this session (not ours), or the reminder was already given
(once per session; DIRIGENT_STOP_MODE=every-turn restores per-turn blocking).
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirigent_common import (read_payload, guards_enabled, find_ledger,
                             parse_ledger, load_marker, save_marker, metric)


def main() -> int:
    payload = read_payload()
    if not guards_enabled(payload):
        return 0
    if payload.get("stop_hook_active"):
        metric("stop_pass", reason="stop_hook_active")
        return 0  # this stop already follows a block — never chain-block
    ledger = find_ledger(payload)
    if ledger is None:
        return 0

    state = parse_ledger(ledger)
    if not state["open"]:
        metric("stop_pass", reason="all_closed")
        return 0

    sid = payload.get("session_id", "")
    marker = load_marker(sid)
    started = marker.get("started")
    try:
        if started is not None and ledger.stat().st_mtime < float(started) - 5.0:
            metric("stop_pass", reason="foreign_ledger")
            return 0  # untouched by this session — another task's ledger
    except OSError:
        pass

    once = os.environ.get("DIRIGENT_STOP_MODE", "once-per-session") != "every-turn"
    reminded = marker.get("reminded_ledgers") or []
    if once and str(ledger) in reminded:
        metric("stop_pass", reason="already_reminded")
        return 0

    marker["reminded_ledgers"] = reminded + [str(ledger)]
    save_marker(sid, marker)
    metric("stop_block", open_items=len(state["open"]))

    items = "\n".join(f"  - [ ] {it}" for it in state["open"][:20])
    more = f"\n  … and {len(state['open']) - 20} more" if len(state["open"]) > 20 else ""
    sys.stderr.write(
        "dirigent close guard: the Requirements Ledger still has open items:\n"
        f"{items}{more}\n"
        "Finish them, defer with explicit user approval (- [~] deferred: reason), "
        "or acknowledge in one line to the user and move on. If the task is "
        "truly abandoned, archive the ledger (rename to "
        "LEDGER-<topic>-archive.md) to silence this for good. "
        "(This reminder fires once per session.)\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
