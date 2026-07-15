#!/usr/bin/env python3
"""SessionEnd hook: remove this session's marker and sweep markers older
than 96 hours. Deliberately minimal — no tmux/teammate handling."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirigent_common import read_payload, marker_path, state_dir, metric

MAX_AGE_S = 96 * 3600


def main() -> int:
    payload = read_payload()
    p = marker_path(payload.get("session_id", ""))
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
    now = time.time()
    swept = 0
    for f in (state_dir() / "sessions").glob("*.json"):
        try:
            if now - f.stat().st_mtime > MAX_AGE_S:
                f.unlink()
                swept += 1
        except OSError:
            pass
    metric("session_end", swept=swept)
    return 0


if __name__ == "__main__":
    sys.exit(main())
