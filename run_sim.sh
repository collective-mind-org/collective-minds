#!/bin/bash
# Run one heavy simulation at a time, with a memory watchdog so a runaway sim dies instead of the desktop.
# Usage: ./run_sim.sh <script.py> [args...]   (env CM_MEM_CAP_MB overrides the default 6000 MB RSS cap)
# Sandbox (2026-09-29): if a local user `cmsim` exists (scripts/setup_sandbox.sh), the repo is copied to
# /Users/Shared/cm-sim and run as cmsim, which cannot read the owner's home (API keys, ssh, push rights). Only data
# files (.json .jsonl .csv .log .txt, no links) are copied back into results/. CM_NO_SANDBOX=1 runs as yourself.
set -u
LOCK=/tmp/cm-sim.lock
CAP_MB=${CM_MEM_CAP_MB:-6000}
if ! mkdir "$LOCK" 2>/dev/null; then echo "another simulation is running (lock $LOCK); refusing to start" >&2; exit 75; fi
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
REPO="$(cd "$(dirname "$0")" && pwd)"
BASE=/Users/Shared/cm-sim
if [ -z "${CM_NO_SANDBOX:-}" ] && id cmsim >/dev/null 2>&1 && [ -x "$BASE/venv/bin/python" ]; then
  SANDBOX=1
  rsync -a --delete --exclude .git --exclude .venv --exclude _site --exclude __pycache__ "$REPO"/ "$BASE/in"/
  sudo -n -u cmsim rsync -a --delete "$BASE/in"/ "$BASE/work"/
  ARGS=(); for a in "$@"; do ARGS+=("${a/#$REPO\//}"); done        # repo-absolute paths -> relative
  cd "$BASE/work" && nice -n 10 sudo -n -u cmsim -H env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 "$BASE/venv/bin/python" "${ARGS[@]}" &
  PID=$!
  rss_mb() { echo $(( $(ps -u cmsim -o rss= 2>/dev/null | awk '{s+=$1} END {print s+0}') / 1024 )); }
  killsim() { sudo -n -u cmsim pkill -9 -u cmsim 2>/dev/null; }
else
  SANDBOX=0
  PY="${CM_PYTHON:-$(dirname "$0")/.venv/bin/python}"   # CM_PYTHON overrides; falls back to python3 if the repo has no .venv (centaur, 2026-09-28)
  [ -x "$PY" ] || PY="$(command -v python3)"
  nice -n 10 "$PY" "$@" &
  PID=$!
  rss_mb() { echo $(( $(ps -o rss= -p $PID 2>/dev/null || echo 0) / 1024 )); }
  killsim() { kill -9 $PID 2>/dev/null; }
fi
trap 'killsim; rmdir "$LOCK" 2>/dev/null' EXIT
while kill -0 $PID 2>/dev/null; do
  RSS_MB=$(rss_mb)
  if [ "$RSS_MB" -gt "$CAP_MB" ]; then echo "run_sim: RSS ${RSS_MB} MB > cap ${CAP_MB} MB, killing" >&2; killsim; break; fi
  sleep 2
done
wait $PID; STATUS=$?
if [ "$SANDBOX" = 1 ]; then   # data only, never code; ledger/credit files are written by the owner, not by sims
  rsync -a --no-links --exclude credits.json --exclude lit_claims.jsonl --exclude lit_queue.json \
    --include='*/' --include='*.json' --include='*.jsonl' --include='*.csv' --include='*.log' --include='*.txt' --exclude='*' \
    "$BASE/work/results"/ "$REPO/results"/
fi
rmdir "$LOCK" 2>/dev/null; trap - EXIT
exit $STATUS
