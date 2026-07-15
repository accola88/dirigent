"""Spawn-guard mechanics inside an enabled (chair) session."""
from conftest import run_hook, make_ledger
from test_optin import spawn_payload, LONG


def enable(env, repo):
    run_hook("session_marker.py", {"session_id": "s1", "cwd": str(repo), "agent": "ops"}, env)


def test_short_spawn_passes(env, repo):
    enable(env, repo)
    r = run_hook("guard_spawn.py", spawn_payload(repo, text="do a tiny thing"), env)
    assert r.returncode == 0


def test_threshold_env_override(env, repo):
    enable(env, repo)
    env["DIRIGENT_THRESHOLD"] = "10"
    r = run_hook("guard_spawn.py", spawn_payload(repo, text="x" * 11), env)
    assert r.returncode == 2


def test_fork_exempt(env, repo):
    enable(env, repo)
    r = run_hook("guard_spawn.py", spawn_payload(repo, sub="fork"), env)
    assert r.returncode == 0


def test_ledger_lets_it_pass(env, repo):
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. something"])
    r = run_hook("guard_spawn.py", spawn_payload(repo), env)
    assert r.returncode == 0


def test_ledger_found_from_subdir(env, repo):
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. something"])
    r = run_hook("guard_spawn.py", spawn_payload(repo / "sub" / "dir"), env)
    assert r.returncode == 0


def test_chair_as_subagent_denied(env, repo):
    """fab/ops are chairs, not workers — denied even for short prompts,
    even with a ledger in place, and even under a plugin namespace."""
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. something"])
    r = run_hook("guard_spawn.py", spawn_payload(repo, text="tiny", sub="fab"), env)
    assert r.returncode == 2
    assert "chair" in r.stderr
    r = run_hook("guard_spawn.py", spawn_payload(repo, text="tiny", sub="dirigent:ops"), env)
    assert r.returncode == 2


def test_workflow_tool_script_gated(env, repo):
    enable(env, repo)
    p = {"session_id": "s1", "cwd": str(repo), "tool_name": "Workflow",
         "tool_input": {"script": LONG}}
    r = run_hook("guard_spawn.py", p, env)
    assert r.returncode == 2


def test_workflow_args_count_toward_threshold(env, repo):
    """A scriptPath re-invocation carries no inline script — but long args
    (string or structured) must still hit the gate; short args pass."""
    enable(env, repo)
    p = {"session_id": "s1", "cwd": str(repo), "tool_name": "Workflow",
         "tool_input": {"scriptPath": "/x/wf.js", "args": LONG}}
    assert run_hook("guard_spawn.py", p, env).returncode == 2
    p["tool_input"]["args"] = {"question": LONG}
    assert run_hook("guard_spawn.py", p, env).returncode == 2
    p["tool_input"]["args"] = ["small"]
    assert run_hook("guard_spawn.py", p, env).returncode == 0


def test_unrelated_tool_ignored(env, repo):
    enable(env, repo)
    p = {"session_id": "s1", "cwd": str(repo), "tool_name": "Bash",
         "tool_input": {"command": LONG}}
    r = run_hook("guard_spawn.py", p, env)
    assert r.returncode == 0


def test_garbage_stdin_never_crashes(env):
    import subprocess, sys
    from conftest import SCRIPTS
    r = subprocess.run([sys.executable, str(SCRIPTS / "guard_spawn.py")],
                       input="not json{{{", capture_output=True, text=True, env=env)
    assert r.returncode == 0
