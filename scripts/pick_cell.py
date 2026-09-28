#!/usr/bin/env python3
"""Pick one CM-BAT-103c cell for a contributor run. Reads the live queue from upstream (so forks see current status),
falls back to the local copy. Prints GitHub Actions outputs: id, k, tau, crate, n."""
import json, os, random, urllib.request
UP = "https://raw.githubusercontent.com/collective-mind-org/collective-minds/main/results/queue_103c.json"
try: q = json.loads(urllib.request.urlopen(UP, timeout=20).read())
except Exception: q = json.load(open("results/queue_103c.json"))
k, tau, c = os.environ.get("IN_K", ""), os.environ.get("IN_TAU", ""), os.environ.get("IN_C", "")
cells = q["cells"]
if k and tau and c:
    pick = next((x for x in cells if x["k"] == float(k) and x["tau"] == float(tau) and x["crate"] == float(c)), None) or \
           {"id": f"103c-k{k}-tau{tau}-c{c}", "k": float(k), "tau": float(tau), "crate": float(c), "n": 300}
else:
    open_ = [x for x in cells if x["status"] == "open"]
    pick = random.choice(open_ or cells)
    if not open_: print("replication=1")   # no open cells: this re-runs a finished one; the report labels it
n = int(os.environ.get("IN_N") or pick.get("n", 300))
for key, val in (("id", pick["id"]), ("k", f"{pick['k']:g}"), ("tau", f"{pick['tau']:g}"), ("crate", f"{pick['crate']:g}"), ("n", str(n))):
    print(f"{key}={val}")
