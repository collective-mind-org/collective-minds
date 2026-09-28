#!/bin/bash
# Run one heavy simulation at a time, with a memory watchdog so a runaway sim dies instead of the desktop.
# Usage: ./run_sim.sh <script.py> [args...]   (env CM_MEM_CAP_MB overrides the default 6000 MB RSS cap)
set -u
LOCK=/tmp/cm-sim.lock
CAP_MB=${CM_MEM_CAP_MB:-6000}
if ! mkdir "$LOCK" 2>/dev/null; then echo "another simulation is running (lock $LOCK); refusing to start" >&2; exit 75; fi
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
PY="${CM_PYTHON:-$(dirname "$0")/.venv/bin/python}"   # CM_PYTHON overrides; falls back to python3 if the repo has no .venv (centaur, 2026-09-28)
[ -x "$PY" ] || PY="$(command -v python3)"
nice -n 10 "$PY" "$@" &
PID=$!
trap 'kill $PID 2>/dev/null; rmdir "$LOCK" 2>/dev/null' EXIT
while kill -0 $PID 2>/dev/null; do
  RSS_MB=$(( $(ps -o rss= -p $PID 2>/dev/null || echo 0) / 1024 ))
  if [ "$RSS_MB" -gt "$CAP_MB" ]; then echo "run_sim: RSS ${RSS_MB} MB > cap ${CAP_MB} MB, killing" >&2; kill -9 $PID; break; fi
  sleep 2
done
wait $PID; STATUS=$?
rmdir "$LOCK" 2>/dev/null; trap - EXIT
exit $STATUS
