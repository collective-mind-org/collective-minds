"""CM-BAT-R12b (rosetta's review of R12, 2026-09-28 19:23): R12's x1 baseline was borrowed from R08's t+ = 0.26 arms
(a different file, and t+ set explicitly to 0.26 while R12 runs the OKane2022 default 0.2594). This reruns the x1
conductivity arm inside R12's own settings: default electrolyte, k=2, tau {1.2, 1.8}, C/2, 300 cycles, 5-cycle chunks.
Usage: ./run_sim.sh results/cm_bat_r12b_baseline.py [N=300]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r12_conductivity", "kappa1"); os.makedirs(OUT, exist_ok=True)
results = {"_meta": {"baseline_for": "CM-BAT-R12", "replaces_borrowed": "CM-BAT-R08 tplus0.26_tau1.2 / tplus0.26_tau1.8",
                     "requested_by": "rosetta", "electrolyte": "OKane2022 default (t+ 0.2594, Nyman2008 conductivity x1)"}}
for tau in (1.2, 1.8):
    tag, r = sw.run(("dfn", 2.0, tau, 0.5, N, 5, OUT))
    results[f"kappa1_tau{tau}"] = r
    print(f"kappa x1 tau={tau}: cycles {r['cycles_completed']}, LLI plating {r['LLI_plating_Ah']:.4f} Ah, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CM-BAT-R12b-baseline.json"), "w"), indent=1)
print("done", flush=True)
