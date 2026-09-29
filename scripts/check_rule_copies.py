#!/usr/bin/env python3
"""exori's guard (2026-09-29): every rule that lives in more than one file carries one identical 'RULE <name> vN: ...'
line in each copy; this fails if any copy is missing it or differs. rosetta showed why the trigger must be in the
text too: three copies once agreed on the rule and disagreed on when it applied."""
import re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIES = {"lit-quote": ["gateway/worker.js", "scripts/lit_record.py", "needs/lit-audit.md"]}
bad = 0
for name, files in COPIES.items():
    found = {}
    for f in files:
        m = re.findall(rf"RULE {name} v\d+:[^`\n]*", open(os.path.join(ROOT, f)).read())
        found[f] = m[0].strip() if m else None
    texts = set(found.values())
    if None in texts or len(texts) != 1:
        bad = 1; print(f"FAIL {name}:"); [print(f"  {f}: {t}") for f, t in found.items()]
    else: print(f"ok   {name}: {len(files)} copies identical")
sys.exit(bad)
