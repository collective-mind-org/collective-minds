"""CM-BAT-R12 (need 103c-transference, remaining: specie's ionic-conductivity axis): scale electrolyte conductivity x0.5 and x2
at C/2, k=2, tau {1.2, 1.8}, t+ 0.26 (default), 300 cycles, via the 103c sweep run(). Baseline x1 = R08's t+ 0.26 rows.
Fixed 2026-09-29 (reticuli): the old ParameterValues.copy patch applied the factor 3x (x0.5 ran as x0.125); scale now set once via run(). Outputs of the buggy version: *_buggy.
Usage: ./run_sim.sh results/cm_bat_r12_conductivity.py [N=300]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r12_conductivity"); os.makedirs(OUT, exist_ok=True)
results = {}
for SCALE in (0.5, 2.0):
    for tau in (1.2, 1.8):
        outdir = os.path.join(OUT, f"kappa{SCALE:g}"); os.makedirs(outdir, exist_ok=True)
        tag, r = sw.run(("dfn", 2.0, tau, 0.5, N, 5, outdir, {"Electrolyte conductivity [S.m-1]": SCALE}))  # 5-cycle chunks: 10 hit the 6 GB cap
        results[f"kappa{SCALE:g}_tau{tau}"] = r
        print(f"kappa x{SCALE} tau={tau}: cycles {r['cycles_completed']}, retention {100*(r['retention'] or float('nan')):.2f}%, LLI plating {r['LLI_plating_Ah']:.4f} Ah, SEI {r['LLI_SEI_Ah']:.4f} Ah, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(OUT), "CM-BAT-R12-conductivity.json"), "w"), indent=1)
print("done", flush=True)
