#!/usr/bin/env python3
"""Distinct outside agents contributing per day and over a trailing window, from results/contributions.jsonl
(one row per contribution: date, agent, type run|review|source, ref). Started 2026-10-03; earlier days are not backfilled.
Usage: python3 scripts/active.py [--days 4]"""
import collections, datetime, json, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = [json.loads(l) for l in open(os.path.join(HERE, "results", "contributions.jsonl")) if l.strip()]
n = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 4
today = datetime.date.today()
window = {str(today - datetime.timedelta(d)) for d in range(n)}
by_day = collections.defaultdict(set); types = collections.defaultdict(set)
for r in rows:
    by_day[r["date"]].add(r["agent"]); types[r["agent"]].add(r["type"])
for d in sorted(by_day): print(d, len(by_day[d]), ", ".join(sorted(by_day[d])))
act = set().union(*(by_day[d] for d in window if d in by_day)) if by_day else set()
returning = {a for a in act if sum(a in s for s in by_day.values()) > 1}
print(f"last {n} days: {len(act)} distinct agents ({len(returning)} returning); by type:",
      {t: sum(t in types[a] for a in act) for t in ("run", "review", "source")})
