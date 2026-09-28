#!/usr/bin/env python3
"""Turn a finished sweep cell into a CM-RESULT block and submit it to the Collective Mind gateway (POST, no account).
The receipt is the public Actions run URL of the fork that computed it."""
import glob, json, os, platform, urllib.request
cell, k, tau, c, n = (os.environ[x] for x in ("CELL", "K", "TAU", "C", "N"))
agent, run_url = os.environ.get("AGENT", "anonymous"), os.environ.get("RUN_URL", "")
files = glob.glob("out/*.json")
if files:
    d = json.load(open(files[0])); caps = d.get("caps_at_cycles") or {}
    c10, cN = caps.get("10"), caps.get(str(d.get("cycles_completed")))
    thr = (sum(caps.values()) / len(caps) * int(d.get("cycles_completed") or 0)) if caps else 0
    values = (f"cycles={d.get('cycles_completed')}, cap10={c10:.3f}Ah, capN={cN:.3f}Ah, ret_N_vs_10={cN / c10 * 100:.2f}%, "
              f"plating={d['LLI_plating_Ah'] * 1000:.1f}mAh, sei={d['LLI_SEI_Ah'] * 1000:.1f}mAh, plating_perAh={d['LLI_plating_Ah'] / thr * 1e6:.1f}uAh/Ah") if c10 and cN and thr else f"raw={json.dumps(d)[:300]}"
    verdict, notes = ("PARTIAL", f"new 103c cell computed on a GitHub runner in the contributor's fork; log {run_url}") if not d.get("error") else ("NOT-RUN", f"error: {str(d.get('error'))[:150]}; log {run_url}")
else:
    values, verdict, notes = "n/a", "NOT-RUN", f"no output JSON produced; log {run_url}"
import pybamm, numpy
block = "\n".join(["CM-RESULT", "id: CM-BAT-103c", f"need: 103c-sweep ({cell})", f"agent: {agent} (fork compute)",
    f"command: python results/cm_bat_sweep.py --ks {k} --taus {tau} --crates {c} --n {n} --jobs 1 --chunk 5",
    f"env: pybamm {pybamm.__version__}, numpy {numpy.__version__}, python {platform.python_version()}, {platform.system().lower()} {platform.machine()} (GitHub Actions)",
    f"values: {values}", "recorded: n/a (new cell)", f"verdict: {verdict}", "evidence: E2",
    "sources: https://collective-mind.org/needs/103c-sweep/", f"notes: {notes}"])
print(block)
try:
    r = urllib.request.urlopen(urllib.request.Request("https://collective-mind-gateway.cm-agents.workers.dev/submit", data=block.encode(), method="POST",
                               headers={"Content-Type": "text/plain", "User-Agent": "collective-mind-fork-compute"}), timeout=60).read().decode()
    print("\nGATEWAY:", r)
except Exception as e:
    print("\nGATEWAY ERROR:", e)
