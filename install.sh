#!/usr/bin/env bash
# dirigent — stage-1 install: agents + /dirigent command (no hooks).
# Afterwards: `claude --agent fab` or `claude --agent ops`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/.claude/agents"
mkdir -p "$DEST"
for f in "$ROOT/agents"/*.md; do
  cp -v "$f" "$DEST/"
done
CMD_DEST="${HOME}/.claude/commands"
mkdir -p "$CMD_DEST"
for f in "$ROOT/commands"/*.md; do
  cp -v "$f" "$CMD_DEST/"
done
WF_DEST="${HOME}/.claude/workflows"
mkdir -p "$WF_DEST"
for f in "$ROOT/workflows"/*.js; do
  cp -v "$f" "$WF_DEST/"
done
echo
echo "Done. Start: claude --agent fab   |   claude --agent ops"
echo "Mid-session activation: /dirigent"
echo "Hooks (stage 2) are separate: see README, Installation section."
