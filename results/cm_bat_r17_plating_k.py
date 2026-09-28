"""CM-BAT-R17 (bytes' question on R14): is the thickness edge a transport effect or an artefact of O'Kane 2022's plating fit?
Reruns the 103c cells at k = 2.5 and 3, tau 1.2 and 1.8, C/2, 300 cycles with the plating kinetic rate constant x0.1 and x10.
Usage: ./run_sim.sh results/cm_bat_r17_plating_k.py [N=300]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pybamm, cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r17_plating_k"); os.makedirs(OUT, exist_ok=True)
_orig_copy = pybamm.ParameterValues.copy
def _copy(self):
    p = _orig_copy(self); p["Lithium plating kinetic rate constant [m.s-1]"] = p["Lithium plating kinetic rate constant [m.s-1]"] * SCALE; return p
pybamm.ParameterValues.copy = _copy
results = {}
for SCALE in (0.1, 10.0):
    for k in (2.5, 3.0):
        for tau in (1.2, 1.8):
            outdir = os.path.join(OUT, f"kpl{SCALE:g}"); os.makedirs(outdir, exist_ok=True)
            tag, r = sw.run(("dfn", k, tau, 0.5, N, 5, outdir)); results[f"kpl{SCALE:g}_k{k:g}_tau{tau}"] = r
            c = r["caps_at_cycles"]
            print(f"kpl x{SCALE:g} k={k:g} tau={tau}: cap10 {c.get('10', float('nan')):.2f} Ah, cap300 {c.get('300', float('nan')):.2f} Ah, plating {r['LLI_plating_Ah']*1000:.0f} mAh, SEI {r['LLI_SEI_Ah']*1000:.0f} mAh, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(OUT), "CM-BAT-R17-plating-k.json"), "w"), indent=1)
print("done", flush=True)
