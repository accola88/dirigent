"""The core promise: guards are SILENT outside dirigent sessions."""
from conftest import run_hook, make_ledger

LONG = "x" * 5000


def spawn_payload(cwd, text=LONG, tool="Agent", sub=""):
    ti = {"prompt": text}
    if sub:
        ti["subagent_type"] = sub
    return {"session_id": "s1", "cwd": str(cwd), "tool_name": tool, "tool_input": ti}


def test_silent_without_any_optin(env, repo):
    """No chair, no .workflow, no env force → long spawn passes untouched."""
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 0 and r.stderr == ""


def test_stop_silent_without_optin(env, repo):
    r = run_hook("guard_stop.py", {"session_id": "s1", "cwd": str(repo)}, env)
    assert r.returncode == 0


def test_env_force_on(env, repo):
    env["DIRIGENT_GUARDS"] = "1"
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 2
    assert "LEDGER" in r.stderr


def test_env_force_off_beats_workflow_dir(env, repo):
    (repo / ".workflow").mkdir()
    env["DIRIGENT_GUARDS"] = "0"
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 0


def test_workflow_dir_enables(env, repo):
    (repo / ".workflow").mkdir()  # dir exists but no LEDGER.md yet
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 2


def test_chair_marker_enables(env, repo):
    run_hook("session_marker.py", {"session_id": "s1", "cwd": str(repo), "agent": "fab"}, env)
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 2


def test_namespaced_plugin_chair_enables(env, repo):
    """Plugin agents arrive namespaced (dirigent:fab) — still a chair."""
    run_hook("session_marker.py",
             {"session_id": "s1", "cwd": str(repo), "agent_type": "dirigent:fab"}, env)
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 2


def test_non_chair_agent_stays_silent(env, repo):
    run_hook("session_marker.py", {"session_id": "s1", "cwd": str(repo), "agent": "code-reviewer"}, env)
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 0
