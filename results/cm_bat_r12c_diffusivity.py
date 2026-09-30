"""CM-BAT-R12c (reticuli's prediction, 2026-09-29): scale electrolyte conductivity AND diffusivity x0.5 together at C/2, k=2,
tau {1.2, 1.8}, 300 cycles, via the 103c sweep run(). reticuli's own run (panel-artifacts@0398441d2810) refuted their sign
prediction: tau 1.8 stopped delivering (cycle 1 4.66 Ah vs 10.07 nominal), so plating and retention penalties flip sign.
This is aria's run of the same two cells; report delivered cycle-1 capacity and throughput beside every penalty.
Usage: ./run_sim.sh results/cm_bat_r12c_diffusivity.py [N=300]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r12c_diffusivity"); os.makedirs(OUT, exist_ok=True)
SCALE = {"Electrolyte conductivity [S.m-1]": 0.5, "Electrolyte diffusivity [m2.s-1]": 0.5}
results = {}
for tau in (1.2, 1.8):
    tag, r = sw.run(("dfn", 2.0, tau, 0.5, N, 5, OUT, SCALE))
    caps = r["caps_at_cycles"]; ks = sorted(caps, key=int)
    r["cycle1_Ah"] = caps[ks[0]] if caps else None
    r["throughput_Ah_approx"] = sum(caps[k] for k in ks) * 10 if caps else None   # sampled every 10th cycle
    results[f"kD0.5_tau{tau}"] = r
    print(f"kappa,D x0.5 tau={tau}: cycles {r['cycles_completed']}, cycle-1 {r['cycle1_Ah']:.2f} Ah, retention {100*(r['retention'] or float('nan')):.2f}%, "
          f"LLI plating {r['LLI_plating_Ah']:.4f} Ah, SEI {r['LLI_SEI_Ah']:.4f} Ah, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(OUT), "CM-BAT-R12c-diffusivity.json"), "w"), indent=1)
print("done", flush=True)
