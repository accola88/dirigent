"""Close-guard mechanics: block once with open items, pass otherwise."""
import os
import time
from conftest import run_hook, make_ledger


def enable(env, repo, sid="s1"):
    run_hook("session_marker.py", {"session_id": sid, "cwd": str(repo), "agent": "fab"}, env)


def stop(env, repo, sid="s1"):
    return run_hook("guard_stop.py", {"session_id": sid, "cwd": str(repo)}, env)


def test_open_items_block_with_listing(env, repo):
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. write tests", "- [x] 2. done thing"])
    r = stop(env, repo)
    assert r.returncode == 2
    assert "write tests" in r.stderr


def test_all_closed_passes(env, repo):
    enable(env, repo)
    make_ledger(repo, ["- [x] 1. a", "- [~] 2. deferred: user said later"])
    assert stop(env, repo).returncode == 0


def test_blocks_only_once_per_session(env, repo):
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. open"])
    assert stop(env, repo).returncode == 2
    assert stop(env, repo).returncode == 0  # second close passes


def test_every_turn_mode(env, repo):
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. open"])
    env["DIRIGENT_STOP_MODE"] = "every-turn"
    assert stop(env, repo).returncode == 2
    assert stop(env, repo).returncode == 2


def test_stop_hook_active_never_chain_blocks(env, repo):
    """A stop that already follows a blocked stop must pass, even in
    every-turn mode — otherwise the guard loops against the block cap."""
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. open"])
    env["DIRIGENT_STOP_MODE"] = "every-turn"
    assert stop(env, repo).returncode == 2
    r = run_hook("guard_stop.py",
                 {"session_id": "s1", "cwd": str(repo), "stop_hook_active": True}, env)
    assert r.returncode == 0
    assert stop(env, repo).returncode == 2  # next regular turn blocks again


def test_second_ledger_gets_its_own_reminder(env, repo, tmp_path):
    """Reminder is scoped per ledger, not per session — a NEW task later in
    the same session must still get its one reminder."""
    enable(env, repo)
    make_ledger(repo, ["- [ ] 1. task one open"])
    assert stop(env, repo).returncode == 2
    assert stop(env, repo).returncode == 0
    repo2 = tmp_path / "repo2"; (repo2 / ".git").mkdir(parents=True)
    make_ledger(repo2, ["- [ ] 1. task two open"])
    assert stop(env, repo2).returncode == 2   # new ledger → new reminder
    assert stop(env, repo2).returncode == 0


def test_foreign_old_ledger_ignored(env, repo):
    make_ledger(repo, ["- [ ] 1. from an old task"])
    old = time.time() - 3600
    lp = repo / ".workflow" / "LEDGER.md"
    os.utime(lp, (old, old))
    enable(env, repo)  # session starts AFTER the ledger's mtime
    assert stop(env, repo).returncode == 0


def test_no_ledger_passes(env, repo):
    enable(env, repo)
    (repo / ".workflow").mkdir()
    assert stop(env, repo).returncode == 0


def test_marker_started_survives_reinjection(env, repo):
    """resume/clear re-fires SessionStart — 'started' must not move."""
    import json
    from conftest import run_hook
    from pathlib import Path
    run_hook("session_marker.py", {"session_id": "s9", "cwd": str(repo), "agent": "ops"}, env)
    sessions = Path(env["DIRIGENT_STATE_DIR"]) / "sessions"
    first = json.loads((sessions / "s9.json").read_text())["started"]
    time.sleep(0.05)
    run_hook("session_marker.py", {"session_id": "s9", "cwd": str(repo)}, env)
    again = json.loads((sessions / "s9.json").read_text())
    assert again["started"] == first
    assert again["chair"] == "ops"  # chair survives a payload without agent field


def test_cleanup_removes_marker_and_sweeps_old(env, repo):
    import json, os
    from conftest import run_hook
    from pathlib import Path
    run_hook("session_marker.py", {"session_id": "gone", "cwd": str(repo)}, env)
    sessions = Path(env["DIRIGENT_STATE_DIR"]) / "sessions"
    stale = sessions / "stale.json"
    stale.write_text("{}")
    old = time.time() - 100 * 3600
    os.utime(stale, (old, old))
    run_hook("cleanup.py", {"session_id": "gone", "cwd": str(repo)}, env)
    assert not (sessions / "gone.json").exists()
    assert not stale.exists()
