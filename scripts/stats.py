#!/usr/bin/env python3
"""Summarize dirigent metrics (~/.claude/dirigent/metrics.jsonl).

Usage:  python3 scripts/stats.py [--days N]     (default: all time)
Shows guard events, per-role delegation counts, background share,
model-override violations, and spawn error rates.
"""
import json, sys, time, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirigent_common import state_dir

days = None
if "--days" in sys.argv:
    try:
        days = float(sys.argv[sys.argv.index("--days") + 1])
    except (IndexError, ValueError):
        print("usage: stats.py [--days N]"); sys.exit(1)
cutoff = time.time() - days * 86400 if days else None

path = state_dir() / "metrics.jsonl"
if not path.is_file():
    print("no metrics yet:", path); sys.exit(0)

events = collections.Counter()
reasons = collections.Counter()
roles = collections.Counter()
role_bg = collections.Counter()
role_err = collections.Counter()
overrides = collections.Counter()
unknown_roles = collections.Counter()
first = last = None

for line in path.read_text().splitlines():
    try:
        rec = json.loads(line)
    except Exception:
        continue
    t = rec.get("t", 0)
    if cutoff and t < cutoff:
        continue
    first = t if first is None else min(first, t)
    last = t if last is None else max(last, t)
    ev = rec.get("event", "?")
    events[ev] += 1
    if rec.get("reason"):
        reasons[(ev, rec["reason"])] += 1
    if ev == "spawn":
        role = rec.get("role", "?")
        roles[role] += 1
        if rec.get("background"):
            role_bg[role] += 1
        if rec.get("errored"):
            role_err[role] += 1
        if rec.get("model_override"):
            overrides[(role, rec["model_override"])] += 1
        if not rec.get("known", True) and role != "(default)":
            unknown_roles[role] += 1

span = f"last {days:g} days" if days else "all time"
print(f"dirigent metrics — {span} ({path})")
if first:
    fmt = lambda ts: time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
    print(f"window: {fmt(first)} → {fmt(last)}")

print("\nguard/session events:")
for ev, n in events.most_common():
    if ev != "spawn":
        print(f"  {ev:15} {n}")
if reasons:
    print("pass reasons:")
    for (ev, r), n in reasons.most_common():
        print(f"  {ev}/{r:20} {n}")

if roles:
    total = sum(roles.values())
    print(f"\ndelegations by role ({total} spawns):")
    print(f"  {'role':12} {'count':>6} {'share':>7} {'bg':>5} {'err':>5}")
    for role, n in roles.most_common():
        print(f"  {role:12} {n:>6} {n/total:>6.0%} {role_bg[role]:>5} {role_err[role]:>5}")

if overrides:
    print("\n⚠ model overrides on named roles (should be zero — roles own routing):")
    for (role, model), n in overrides.most_common():
        print(f"  {role} ← {model}: {n}×")
if unknown_roles:
    print("\nad-hoc/unknown subagent types:")
    for role, n in unknown_roles.most_common():
        print(f"  {role}: {n}×")
