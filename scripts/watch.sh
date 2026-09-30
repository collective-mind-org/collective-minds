#!/bin/bash
# Event-driven loop (2026-09-30): run heartbeat every 3 min; print ONLY when something is new (one line per item).
# Silence = nothing new. Heartbeat errors are printed too (never silent on failure). Used via Claude Code's Monitor tool.
cd "$(dirname "$0")/.." || exit 1
while true; do
  out=$(timeout 150 python3 heartbeat.py 2>&1); rc=$?
  if [ $rc -eq 3 ]; then
    echo "$out" | python3 -c '
import sys,re
txt=sys.stdin.read(); blocks=re.split(r"\n(?=\[)", txt.split("\n",1)[1] if "\n" in txt else "")
for b in blocks:
    b=b.strip()
    if b: print("NEW " + re.sub(r"\s+"," ",b)[:400], flush=True)'
  elif [ $rc -ne 0 ]; then
    echo "HEARTBEAT-ERROR rc=$rc $(echo "$out" | tail -2 | tr '\n' ' ' | cut -c1-200)"
  fi
  sleep 180
done
