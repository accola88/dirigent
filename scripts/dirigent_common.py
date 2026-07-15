"""Shared helpers for dirigent hooks. Own implementation, MIT."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

CHAIRS = {"fab", "ops"}


def read_payload() -> dict:
    """Hook input arrives as JSON on stdin; never crash on bad input."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def state_dir() -> Path:
    d = Path(os.environ.get("DIRIGENT_STATE_DIR", str(Path.home() / ".claude" / "dirigent")))
    (d / "sessions").mkdir(parents=True, exist_ok=True)
    return d


def marker_path(session_id: str) -> Path:
    safe = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_") or "unknown"
    return state_dir() / "sessions" / f"{safe}.json"


def load_marker(session_id: str) -> dict:
    p = marker_path(session_id)
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def save_marker(session_id: str, data: dict) -> None:
    try:
        marker_path(session_id).write_text(json.dumps(data))
    except Exception:
        pass


def repo_root(start: Path) -> Path:
    """Walk up to the git root; stop at $HOME or filesystem root."""
    home = Path.home()
    cur = start.resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur == home or cur.parent == cur:
            return start.resolve()
        cur = cur.parent


def find_upward(start: Path, rel: str) -> Path | None:
    """Search start → repo root (inclusive) for a relative path."""
    root = repo_root(start)
    cur = start.resolve()
    while True:
        cand = cur / rel
        if cand.exists():
            return cand
        if cur == root or cur.parent == cur:
            return None
        cur = cur.parent


def guards_enabled(payload: dict) -> bool:
    """Opt-in gate: guards are silent unless the user is in dirigent mode.

    Precedence: DIRIGENT_GUARDS=0 forces off, =1 forces on. Otherwise:
    enabled if the session marker names a chair (fab/ops) OR a ./.workflow
    directory exists between cwd and the repo root.
    """
    forced = os.environ.get("DIRIGENT_GUARDS", "").strip()
    if forced == "0":
        return False
    if forced == "1":
        return True
    marker = load_marker(payload.get("session_id", ""))
    if marker.get("chair") in CHAIRS:
        return True
    cwd = Path(payload.get("cwd") or os.getcwd())
    return find_upward(cwd, ".workflow") is not None


def find_ledger(payload: dict) -> Path | None:
    cwd = Path(payload.get("cwd") or os.getcwd())
    return find_upward(cwd, os.path.join(".workflow", "LEDGER.md"))


def delegation_chars(ti: dict) -> int:
    """Size of everything text-bearing in a spawn call. `args` counts too — a
    workflow's payload can hide there; a scriptPath re-invocation carries no
    inline script (it was gated when first submitted inline)."""
    n = sum(len(str(ti.get(k) or "")) for k in ("prompt", "script", "description"))
    args = ti.get("args")
    if args is not None:
        n += len(args) if isinstance(args, str) else len(json.dumps(args))
    return n


def parse_ledger(path: Path) -> dict:
    """Count checkbox states. Open = '- [ ]', done = '- [x]', deferred = '- [~]'."""
    open_items, done, deferred = [], 0, 0
    try:
        for line in path.read_text(errors="replace").splitlines():
            s = line.strip()
            if s.startswith("- [ ]"):
                open_items.append(s[5:].strip())
            elif s.lower().startswith("- [x]"):
                done += 1
            elif s.startswith("- [~]"):
                deferred += 1
    except Exception:
        pass
    return {"open": open_items, "done": done, "deferred": deferred}


def metric(event: str, **fields) -> None:
    """Append one event line (never prompt content). DIRIGENT_METRICS=0 disables."""
    if os.environ.get("DIRIGENT_METRICS", "").strip() == "0":
        return
    try:
        rec = {"t": int(time.time()), "event": event}
        rec.update(fields)
        with (state_dir() / "metrics.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
