"""CM-BAT-R10 (need 103c-transference, remaining part): the R08 four runs at 1C charge/discharge instead of C/2.
Does the transference-number effect on the tortuosity lever grow with rate? k=2, tau {1.2, 1.8}, t+ {0.26, 0.40}, N cycles.
Usage: ./run_sim.sh results/cm_bat_r10_tplus_1c.py [N=300]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pybamm, cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r10_tplus_1c"); os.makedirs(OUT, exist_ok=True)
_orig_copy = pybamm.ParameterValues.copy
def _copy(self):
    p = _orig_copy(self); p["Cation transference number"] = TPLUS; return p
pybamm.ParameterValues.copy = _copy
results = {}
for TPLUS in (0.26, 0.40):
    for tau in (1.2, 1.8):
        outdir = os.path.join(OUT, f"tplus{TPLUS:.2f}"); os.makedirs(outdir, exist_ok=True)
        tag, r = sw.run(("dfn", 2.0, tau, 1.0, N, 10, outdir))  # chunk 10: the 30-cycle chunk hit the 6 GB RSS cap at 1C
        results[f"tplus{TPLUS:.2f}_tau{tau}"] = r
        print(f"t+={TPLUS} tau={tau} 1C: cycles {r['cycles_completed']}, retention {100*(r['retention'] or float('nan')):.2f}%, LLI plating {r['LLI_plating_Ah']:.4f} Ah, SEI {r['LLI_SEI_Ah']:.4f} Ah, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(OUT), "CM-BAT-R10-tplus-1c.json"), "w"), indent=1)
print("done", flush=True)
