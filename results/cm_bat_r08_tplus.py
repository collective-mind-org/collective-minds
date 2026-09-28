"""CM-BAT-R08 (need 103c-transference): sensitivity of the tortuosity effect on plating LLI to the cation transference number.
Runs the CM-BAT sweep's run() for k=2, tau in {1.2, 1.8}, C/2, N cycles, at t+ = 0.26 (OKane2022 default) and t+ = 0.40.
Wrapper: monkey-patches the parameter set inside cm_bat_sweep.run via pybamm.ParameterValues so the sweep script stays unchanged.
Usage: ./run_sim.sh results/cm_bat_r08_tplus.py [N=300]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pybamm, cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r08_tplus"); os.makedirs(OUT, exist_ok=True)
_orig_copy = pybamm.ParameterValues.copy
def _copy(self):
    """copy() that applies the requested transference number; sw.run() calls base.copy() once per job."""
    p = _orig_copy(self); p["Cation transference number"] = TPLUS; return p
pybamm.ParameterValues.copy = _copy
results = {}
for TPLUS in (0.26, 0.40):
    for tau in (1.2, 1.8):
        outdir = os.path.join(OUT, f"tplus{TPLUS:.2f}"); os.makedirs(outdir, exist_ok=True)
        tag, r = sw.run(("dfn", 2.0, tau, 0.5, N, 30, outdir))
        results[f"tplus{TPLUS:.2f}_tau{tau}"] = r
        print(f"t+={TPLUS} tau={tau}: cycles {r['cycles_completed']}, retention {100*(r['retention'] or float('nan')):.2f}%, LLI plating {r['LLI_plating_Ah']:.4f} Ah, SEI {r['LLI_SEI_Ah']:.4f} Ah, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(OUT), "CM-BAT-R08-tplus.json"), "w"), indent=1)
print("done", flush=True)
