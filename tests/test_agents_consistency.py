"""Lint the agent files: every role the chairs route to must exist, with
valid frontmatter — catches rename drift before it hits a session."""
import re
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1] / "agents"
ROLES = {"scout", "mech", "coder", "judge", "esc", "sec", "plan-check", "check", "check-max"}
CHAIRS = {"fab", "ops"}
VALID_EFFORT = {"low", "medium", "high", "xhigh", "max"}
VALID_MODEL = re.compile(r"^(haiku|sonnet|opus|fable|inherit|claude-[a-z0-9.-]+)$")


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path.name}: missing frontmatter"
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def test_all_expected_files_exist():
    names = {p.stem for p in AGENTS.glob("*.md")}
    assert ROLES | CHAIRS <= names, f"missing: {(ROLES | CHAIRS) - names}"


def test_name_matches_filename_and_fields_valid():
    for p in AGENTS.glob("*.md"):
        fm = frontmatter(p)
        assert fm.get("name") == p.stem, f"{p.name}: name != filename"
        assert fm.get("description"), f"{p.name}: empty description"
        assert VALID_MODEL.match(fm.get("model", "")), f"{p.name}: bad model {fm.get('model')}"
        if "effort" in fm:
            assert fm["effort"] in VALID_EFFORT, f"{p.name}: bad effort {fm['effort']}"


def test_chairs_route_to_existing_roles_only():
    for chair in CHAIRS:
        body = (AGENTS / f"{chair}.md").read_text()
        for role in ROLES:
            assert re.search(rf"\b{re.escape(role)}\b", body), \
                f"{chair}.md does not mention role '{role}'"


def test_routing_matrix():
    expected = {
        "scout": ("haiku", "low"), "mech": ("sonnet", "low"),
        "coder": ("sonnet", "xhigh"), "judge": ("sonnet", "high"),
        "esc": ("opus", "high"), "sec": ("opus", "high"),
        "plan-check": ("sonnet", "high"), "check": ("sonnet", "high"), "check-max": ("inherit", "max"),
    }
    for role, (model, effort) in expected.items():
        fm = frontmatter(AGENTS / f"{role}.md")
        assert fm["model"] == model, f"{role}: model {fm['model']} != {model}"
        assert fm["effort"] == effort, f"{role}: effort {fm.get('effort')} != {effort}"


def test_verifiers_cannot_write_or_spawn():
    for role in ("check", "check-max"):
        fm = frontmatter(AGENTS / f"{role}.md")
        d = fm.get("disallowedTools", "")
        for tool in ("Write", "Edit", "Agent"):
            assert tool in d, f"{role}: {tool} not disallowed"


def test_plan_check_is_read_only():
    fm = frontmatter(AGENTS / "plan-check.md")
    assert fm.get("tools") == "Read, Glob, Grep"


def test_chairs_have_no_tools_allowlist():
    """A tools allowlist on the chair would strip MCP tools from the session."""
    for chair in CHAIRS:
        fm = frontmatter(AGENTS / f"{chair}.md")
        assert "tools" not in fm, f"{chair}: remove tools allowlist (MCP loss)"


def test_dirigent_command_routes_to_existing_roles():
    """The /dirigent command duplicates the routing table — keep it in sync."""
    cmd = AGENTS.parent / "commands" / "dirigent.md"
    assert cmd.is_file(), "commands/dirigent.md missing"
    fm = frontmatter(cmd)
    assert fm.get("description"), "dirigent.md: empty description"
    body = cmd.read_text()
    for role in ROLES:
        assert re.search(rf"\b{re.escape(role)}\b", body), \
            f"dirigent.md does not mention role '{role}'"


def test_chairs_pin_security_to_opus_and_forbid_invocation_model():
    for chair in CHAIRS:
        body = (AGENTS / f"{chair}.md").read_text().lower()
        assert "omit the `model` argument" in body
        assert "sec" in body and "opus" in body
