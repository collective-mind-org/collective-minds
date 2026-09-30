"""CM-BAT-R12e (break test named in R12d, 2026-09-30): at C/2 the κ,D×0.5 τ1.8 cell delivers 47 % of nominal and its plating
penalty flips sign. At C/5 the discharge should not hit 2.5 V early; prediction: cycle-1 delivery > 80 % of nominal in both
cells and the τ1.8 plating penalty positive again. Same cells as R12c (k=2, τ 1.2/1.8, conductivity and diffusivity ×0.5),
100 cycles at C/5. Usage: ./run_sim.sh results/cm_bat_r12e_c5.py [N=100]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_sweep as sw
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r12e_c5"); os.makedirs(OUT, exist_ok=True)
SCALE = {"Electrolyte conductivity [S.m-1]": 0.5, "Electrolyte diffusivity [m2.s-1]": 0.5}
results = {}
for tau in (1.2, 1.8):
    tag, r = sw.run(("dfn", 2.0, tau, 0.2, N, 5, OUT, SCALE)); results[f"tau{tau}"] = r
    print(f"C/5 kappa,D x0.5 tau={tau}: cycles {r['cycles_completed']}, cycle-1 frac {r.get('cycle1_frac_nominal')}, retention {100*(r['retention'] or float('nan')):.2f}%, plating {1000*r['LLI_plating_Ah']:.1f} mAh, err={r['error']}", flush=True)
json.dump(results, open(os.path.join(os.path.dirname(OUT), "CM-BAT-R12e-c5.json"), "w"), indent=1)
print("done", flush=True)
