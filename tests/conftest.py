import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolated state dir + clean dirigent env for every test."""
    state = tmp_path / "state"
    e = {k: v for k, v in os.environ.items() if not k.startswith("DIRIGENT_")}
    e["DIRIGENT_STATE_DIR"] = str(state)
    e["DIRIGENT_METRICS"] = "1"
    return e


def run_hook(script: str, payload: dict, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


@pytest.fixture()
def repo(tmp_path):
    """A fake git repo working dir."""
    r = tmp_path / "repo"
    (r / ".git").mkdir(parents=True)
    (r / "sub" / "dir").mkdir(parents=True)
    return r


def make_ledger(repo: Path, lines):
    wf = repo / ".workflow"
    wf.mkdir(exist_ok=True)
    (wf / "LEDGER.md").write_text("\n".join(lines) + "\n")
    return wf / "LEDGER.md"


@pytest.fixture()
def started_session(env):
    """Simulate SessionStart for session 's1' and return its env."""
    run_hook("session_marker.py", {"session_id": "s1", "cwd": "/"}, env)
    return env
