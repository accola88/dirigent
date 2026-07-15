"""Edge-shape robustness: hooks must fail open on malformed payloads,
tolerate corrupted state, and never share state across identity-less
sessions. Found by running the shipped fanout-analysis workflow on the
hook scripts themselves (07/2026)."""
import json
import subprocess
import sys
from pathlib import Path

from conftest import run_hook, make_ledger, SCRIPTS


def enable(env, repo):
    run_hook("session_marker.py", {"session_id": "s1", "cwd": str(repo), "agent": "ops"}, env)


def test_non_dict_payload_and_tool_input_fail_open(env, repo):
    """Valid JSON that is not a dict, and tool_input that is a list, must
    pass silently — a crashed hook is a silently absent guard."""
    enable(env, repo)
    r = subprocess.run([sys.executable, str(SCRIPTS / "guard_spawn.py")],
                       input='["not", "a", "dict"]', capture_output=True,
                       text=True, env=env)
    assert r.returncode == 0 and not r.stderr
    p = {"session_id": "s1", "cwd": str(repo), "tool_name": "Agent",
         "tool_input": ["x" * 5000]}
    assert run_hook("guard_spawn.py", p, env).returncode == 0
    assert run_hook("track_spawn.py", p, env).returncode == 0


def test_corrupted_marker_started_never_crashes(env, repo):
    """A hand-edited/corrupted marker ('started' not a number) must not
    crash the stop guard — foreign-check is skipped, blocking still works."""
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. open"])
    sessions = Path(env["DIRIGENT_STATE_DIR"]) / "sessions"
    (sessions / "s1.json").write_text(json.dumps({"started": "garbage", "chair": "ops"}))
    r = run_hook("guard_stop.py", {"session_id": "s1", "cwd": str(repo)}, env)
    assert r.returncode == 2
    assert "open" in r.stderr


def test_chair_detection_is_case_insensitive(env, repo):
    """'OPS' as agent_type must arm the guards; 'FAB' as subagent_type must
    still hit the chair deny — casing is not under our control."""
    run_hook("session_marker.py",
             {"session_id": "s1", "cwd": str(repo), "agent_type": "OPS"}, env)
    p = {"session_id": "s1", "cwd": str(repo), "tool_name": "Agent",
         "tool_input": {"prompt": "x" * 5000}}
    assert run_hook("guard_spawn.py", p, env).returncode == 2
    p["tool_input"] = {"prompt": "tiny", "subagent_type": "FAB"}
    assert run_hook("guard_spawn.py", p, env).returncode == 2


def test_missing_session_id_shares_no_state(env, repo):
    """Without a session_id there is no safe dedup identity: the stop guard
    must not read/write the shared 'unknown' marker (cross-session bleed),
    and the session marker must not create it."""
    make_ledger(repo, ["- [ ] 1. open"])
    env["DIRIGENT_GUARDS"] = "1"
    r1 = run_hook("guard_stop.py", {"cwd": str(repo)}, env)
    r2 = run_hook("guard_stop.py", {"cwd": str(repo)}, env)
    assert r1.returncode == 2 and r2.returncode == 2  # no phantom dedup
    run_hook("session_marker.py", {"cwd": str(repo)}, env)
    assert not (Path(env["DIRIGENT_STATE_DIR"]) / "sessions" / "unknown.json").exists()
