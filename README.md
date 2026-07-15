# dirigent

Optional two-config orchestrator for Claude Code (CLI and VS Code extension).
The chair plans, arbitrates, and decides; named worker roles carry the token
volume on cheaper models; an escalation/verification valve protects quality.
Guard hooks enforce the ledger discipline mechanically — and stay completely
silent outside dirigent sessions.

All numbers in this README come from our own benchmark (07/2026, identical
tasks across all setups, official API pricing). Version 0.2.0.

```text
              CHAIR  fab = Fable 5   |   ops = Opus 4.8
              plan · arbitrate · decide
                            │  specs & ledger down · briefs & verdicts up
   ┌──────────┬─────────────┼─────────────┬──────────────┐
 scout       mech         coder         judge          VALVE
 haiku·low   sonnet·low   sonnet·xhigh  sonnet·high    uncertain/2× fail
 grep·scan   fetch·format code·tests    briefs·review    → esc  opus·high
                                                        security → sec opus·high
              PLAN (large/risky): plan-check sonnet·high → READY/REVISE,
                     then explicit user approval before implementation
              CLOSE: routine → check sonnet·high
                     critical → check-max  (chair model·max, via inherit)
```

## What it is — and what it is not

dirigent is a **session discipline**: roles with pinned models and tools, a
file-based Requirements Ledger that survives context compaction, and hooks
that mechanically secure exactly the two points that get skipped under
pressure (delegation without a spec, closing with open items).

dirigent is **not an automatic cost saver**. Measured: for tasks that fit
comfortably in one context, full orchestration is more expensive and slower
than a solo session — at equal quality. The strengths lie elsewhere (see
"Where the advantages are — and where they aren't").

## Usage

### Installation

**Stage 1 — agents + command (recommended to start):**

```bash
./install.sh          # agents/*.md → ~/.claude/agents/, commands/*.md → ~/.claude/commands/
claude --agent ops    # or: claude --agent fab
```

**Stage 2 — guard hooks (manual):** copy `scripts/*.py` to
`~/.claude/hooks/dirigent/` and merge the block from `hooks/hooks.json`
into `~/.claude/settings.json` (replace `${CLAUDE_PLUGIN_ROOT}` with the
path). **As a plugin:**
`/plugin marketplace add accola88/dirigent` → `/plugin install dirigent@dirigent`
— ships agents, command, and hooks together.

**Stage 3 — per project:** `.claude/settings.json` in the repo:
`{ "agent": "ops" }`. Add `./.workflow/` to `.gitignore`.

### Activating

| Path | Effect |
| --- | --- |
| `claude --agent fab\|ops` | This session runs as the chair |
| Project setting `{ "agent": "ops" }` | Every NEW session in the project runs as the chair (VS Code too) |
| `/dirigent` mid-session | Arms the guards immediately and loads the chair discipline into the running session |
| `/dirigent fab\|ops` | Additionally writes the project setting (one approval click — settings files are protected); NEW sessions start as a real chair; the running one cannot switch its model |
| Addressing roles directly | "use scout/coder for …" works in any session — the roles are installed globally |

### Deactivating

Start without the flag. The hooks deactivate themselves: active only when
the session runs as `fab`/`ops` or `./.workflow/` exists.
**Kill switch / force:** `DIRIGENT_GUARDS=0` or `=1`.

### Configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `DIRIGENT_GUARDS` | (auto) | `0` = guards hard off, `1` = hard on |
| `DIRIGENT_THRESHOLD` | `1500` | Character threshold of the spawn guard (measured across prompt/script/description/args) |
| `DIRIGENT_STOP_MODE` | `once-per-session` | `every-turn` = close guard reminds every turn |
| `DIRIGENT_METRICS` | on | `0` = no metrics logging |

**Analysis:** `python3 scripts/stats.py [--days N]` — guard rates,
delegations per role (share/background/errors), model-override warnings.
Events land in `~/.claude/dirigent/metrics.jsonl`, never prompt content.

## What makes sense when (measured)

This ladder is also built into Rule 0 of the chair prompts since v0.2.0:

| Task | Best measured choice |
| --- | --- |
| Small, well-bounded | ops chair directly ($0.78) or Fable solo ($1.28) — no ceremony |
| Medium, fits in one context | Solo session ($1.83 / 5 min) — or ONE spawn to `coder`/`judge` with the whole task |
| Parallelizable volume + coverage/verification wanted | ONE flat wave of cheap workers + one `check` pass (~$2.50 / 5 min measured as a workflow) |
| Security review | dirigent `sec` lane — the only measured path without a Fable refusal |
| Critical/irreversible close | Ceremony with `check`/`check-max` — the surcharge is an insurance premium |
| Larger than one context, multi-session | Full ceremony — the ledger IS the memory (costs untested there) |

## Comparison: normal (solo) · dirigent · ultracode/workflows

Identical analysis task (8 files, ~3.5k lines), official API pricing, equal
measured quality (16/16 required findings each, citation spot checks 6/6
correct):

| Setup | Cost | Time | Characteristics |
| --- | --- | --- | --- |
| Solo (Fable) | $1.83 | 5 min | Cheap and fast; no verification, no refusal protection |
| Workflow, Sonnet agents | $2.48 | 5 min | Fan-out + built-in adversarial verifier; script must be written per task |
| dirigent ops chair | $3.62 | 19 min | Autonomous orchestration, ledger, `check` verification |
| dirigent fab chair | $6.23 | 31 min | Most expensive coordination (Fable tokens ×2) |
| ultracode default (Fable agents) | $7.09 | 12 min | Maximum coverage, but agents inherit the expensive session model |

Small task (3 files): ops chair solo $0.78 beats Fable solo $1.28 —
Opus tokens officially cost half of Fable.

**Placing ultracode:** ultracode/workflows are a *task tool* (a
deterministic script orchestrates an agent swarm per job); dirigent is a
*session discipline* (roles, ledger, guards across the whole session).
They don't compete — they combine: a workflow whose agents run on Sonnet
via `model` overrides (row 2 of the table) is dirigent's arbitrage idea in
workflow form, and was the best measured multi-agent arm. ultracode in its
default (agents inherit the session model) was the most expensive one.

### Shipped recipe: `fanout-analysis` (the measured winner, ready to use)

The winning arm from the table ships with dirigent as a reusable workflow:
[`workflows/fanout-analysis.js`](workflows/fanout-analysis.js) — N parallel
Sonnet readers → one Sonnet synthesizer → one adversarial Sonnet verifier
that re-opens the cited lines. `install.sh` copies it to
`~/.claude/workflows/`; alternatively place it in a project's
`.claude/workflows/`.

**Invoke it** from any Claude Code session by asking for it by name — the
word "ultracode" in your message (or an explicit "run a workflow") opts the
session into multi-agent orchestration:

```text
ultracode: run the fanout-analysis workflow on this repo —
root /abs/path/to/repo, files src/a.py src/b.py src/c.py src/d.py,
task "error handling and encoding robustness"
```

Claude then calls the Workflow tool with
`{name: "fanout-analysis", args: {root, files: [...], task}}`. The report
comes back as text (workflow subagents are not allowed to write report
files — the session persists it), followed by the verifier's
`Verdict: n/6 correct` line.

Note: like agents and hooks, saved workflows are loaded at **session
start** — after installing, the name resolves in new sessions only. In an
already-running session, point Claude at the script file instead ("run the
workflow script at `…/workflows/fanout-analysis.js` with args …"); the
Workflow tool accepts a `scriptPath` directly.

**How the trick works — and how to build your own:** the entire cost
advantage is one option on each `agent()` call in the script:

```js
const OPTS = { model: 'sonnet', effort: 'high' }   // dirigent's arbitrage idea
agent(prompt, { ...OPTS, label: 'read:...' })
```

Without it, workflow agents inherit the session model — run the same script
from a Fable session and you get the most expensive row of the table
instead of the second-cheapest. Use `haiku` for pure scanning stages and
keep `sonnet·high` for judgment stages; that mirrors dirigent's role
routing (`scout` vs. `judge`) inside a workflow. Reserve this recipe for
tasks that actually split into independent parts — single reasoning chains
(an unknown bug, one architecture decision) stay solo, exactly as Rule 0
says.

## Where the advantages are — and where they aren't

**Advantages (evidenced):**

- **Refusal insurance:** Fable solo hard-refused a benign security review
  ($2.50 burned, no result); `sec` on Opus delivered the finished analysis.
  For security work the route is not a cost question but a delivery
  guarantee.
- **Mechanical verification:** `check`/`check-max` actually run before the
  close; the close guard blocks open ledger items. Solo sessions have no
  counterpart.
- **Small tasks on the ops chair** are cheaper than on Fable.
- **Persistence:** ledger and guards survive compaction and sessions —
  relevant for work spanning days or weeks.
- **Against ultracode's default:** half the price at equal quality.

**No advantages (equally evidenced):**

- **Cost on in-context tasks:** full orchestration = 2× (ops) to 3.4× (fab)
  the solo cost and 4–6× the time, without measurable quality gain.
  Coordination itself is the cost block: the chair wrote ~3× more tokens
  coordinating than the solo session spent solving.
- **The fab chair as a cost saver:** at medium size the most expensive
  dirigent arm — Fable coordination costs twice per token, and its
  verification zeal doubled the worker volume.
- **Speed:** ceremony is always slower than solo or a flat workflow fan-out.

## What the hooks enforce

- **Spawn guard** (`PreToolUse` on Agent|Task|Workflow): delegation
  > `DIRIGENT_THRESHOLD` chars without `./.workflow/LEDGER.md` → DENY.
  Chairs (`fab`/`ops`) as subagents → DENY, regardless of length and ledger.
  Forks and short spawns always pass the ledger gate.
- **Close guard** (`Stop`): open `- [ ]` items block the close — once per
  session. A stop directly after a block (`stop_hook_active`) always
  passes. Ledgers whose mtime predates session start count as foreign.
- **Spawn tracker** (`PostToolUse`): logs per delegation the role,
  background flag, size bucket, error flag, and model overrides (should be
  0 — roles own their routing). Never prompt content.
- **Cleanup** (`SessionEnd`): session marker removed, stale markers
  (>96 h) swept.

## Honest assessment

dirigent solves a real problem — but a different one than its tagline
suggests. The frugality thesis ("chair + cheap workers < big model
everywhere") measurably does **not** hold for tasks that fit in one
context; solo wins there. What remains and carries: model arbitrage as a
principle (it also won as a workflow variant), the reliability layer
(sec lane, verification, guards), and session persistence. Run dirigent as
the default for everything and you pay extra; use it deliberately
(security, critical closes, long projects, small tasks on ops) and you get
properties available nowhere else as a package.

In the ecosystem (research 07/2026): exactly one public project covers the
same combination — Rylaa/fable5-orchestrator, dirigent's direct template
(~17 ★). The closest independent relative, pilotfish (~460 ★), deliberately
omits the ledger and the guard hooks. The big frameworks (oh-my-claudecode,
claude-flow, tens of thousands of ★ each) orchestrate on different axes —
workflow modes and swarms instead of frugal chair economics; the popular
subagent collections pin models but enforce nothing. Nobody publicly beats
dirigent's triad (arbitrage + mechanical guards + ledger + refusal-aware
security pinning) — the differentiation is real but narrow, and the most
honest difference from all of the above is this README: our own
measurements instead of quoted benchmarks.

Open questions: tasks beyond a single context window (dirigent's actual
target zone) are untested — the attempt died at the usage limit. All
comparison numbers are n=1 per arm, one task genre (read-heavy analysis),
and how subscription limits weight the models internally is not measurable
from the outside.

## Honest limits (technical)

- Hooks check ledger existence and checkbox state, not content fidelity.
- A workflow re-invocation via `scriptPath` carries no inline script —
  only `args` are measured then; the script was gated when first submitted.
- `check`/`check-max` need Bash for test reruns and could in principle
  write through it — "never edits" is prompt discipline there;
  `sec` by contrast is genuinely read-only (no Bash).
- `plan-check` (Sonnet) may review plans of a stronger chair — the value
  is fresh-context coverage, not superior insight.
- `metrics.jsonl` grows unbounded (events are tiny; delete when needed).
- A fully closed old ledger in the same directory satisfies the gate for a
  new task (the mtime heuristic only catches older ledgers).
- `check-max` uses `model: inherit` as the ceiling mechanism — verify once
  in your own setup.
- Routing itself is prompt-level; the hooks secure exactly the two points
  that get skipped under pressure.

## Tests

```bash
python3 -m pytest tests/ -q     # 44 tests: opt-in gate, guards+tracker e2e, role/script/command lint
```

## Design sources & related projects

Independent implementation. Patterns informed by:
[Rylaa/fable5-orchestrator](https://github.com/Rylaa/fable5-orchestrator)
(ledger + guard-hook idea; functionally equivalent template),
[pilotfish](https://github.com/Nanako0129/pilotfish) (roles own routing,
escalation discipline — deliberately without ledger/guards), JeredBlu
frugal-fable (context firewall/disk handoff), and Anthropic's multi-agent
benchmark (Fable chair + Sonnet workers ≈ 96% performance at 46% cost —
applies to tasks beyond a single context window; our own measurements at
in-context sizes above).

## License

MIT
