"""Spawn-tracker mechanics: one 'spawn' event per delegation, opt-in like
the guards, and never any prompt content."""
import json
from pathlib import Path

from conftest import run_hook

PROMPT = "secret task content " * 10


def enable(env, repo):
    run_hook("session_marker.py", {"session_id": "s1", "cwd": str(repo), "agent": "ops"}, env)


def track(env, repo, ti, tool="Agent", resp=None):
    p = {"session_id": "s1", "cwd": str(repo), "tool_name": tool, "tool_input": ti}
    if resp is not None:
        p["tool_response"] = resp
    return run_hook("track_spawn.py", p, env)


def spawn_events(env):
    path = Path(env["DIRIGENT_STATE_DIR"]) / "metrics.jsonl"
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text().splitlines()
            if json.loads(l).get("event") == "spawn"]


def test_silent_without_optin(env, repo):
    """No chair, no .workflow → the tracker logs nothing at all."""
    r = track(env, repo, {"subagent_type": "coder", "prompt": PROMPT})
    assert r.returncode == 0
    assert spawn_events(env) == []


def test_logs_role_flags_and_bucket_but_no_content(env, repo):
    enable(env, repo)
    track(env, repo, {"subagent_type": "coder", "prompt": PROMPT,
                      "run_in_background": True})
    (ev,) = spawn_events(env)
    assert ev["role"] == "coder" and ev["known"] is True
    assert ev["background"] is True and ev["errored"] is False
    assert ev["chars"] == "<=500" and ev["model_override"] == ""
    assert "secret" not in json.dumps(ev)  # events, never prompt content


def test_model_override_and_error_recorded(env, repo):
    enable(env, repo)
    track(env, repo, {"subagent_type": "coder", "prompt": "x", "model": "opus"},
          resp={"is_error": True})
    (ev,) = spawn_events(env)
    assert ev["model_override"] == "opus" and ev["errored"] is True


def test_namespaced_role_known_unknown_flagged(env, repo):
    enable(env, repo)
    track(env, repo, {"subagent_type": "dirigent:judge", "prompt": "x"})
    track(env, repo, {"subagent_type": "my-random-agent", "prompt": "x"})
    ns, unknown = spawn_events(env)
    assert ns["role"] == "dirigent:judge" and ns["known"] is True
    assert unknown["known"] is False


def test_default_and_unrelated_tool(env, repo):
    """No subagent_type → '(default)'; non-spawn tools are ignored."""
    enable(env, repo)
    track(env, repo, {"prompt": "x"})
    track(env, repo, {"command": "ls"}, tool="Bash")
    (ev,) = spawn_events(env)
    assert ev["role"] == "(default)"


def test_workflow_args_reach_size_bucket(env, repo):
    """The tracker measures like the spawn guard: args count."""
    enable(env, repo)
    track(env, repo, {"scriptPath": "/x/wf.js", "args": "z" * 6000}, tool="Workflow")
    (ev,) = spawn_events(env)
    assert ev["chars"] == ">5000"
