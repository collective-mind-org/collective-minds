"""CM-BAT-R19c: second hypothesis after R19b falsified solid diffusion; falsify R19's explanation. R19: the DFN breaks the MEASURED self-similarity (54 um/4C plates at 16-33 %
Hypothesis 2: the model's high-rate onset is set by the charge-transfer overpotential (scales with C, not L^2*C); test j0 x10, x100.
diffusion (Chen2020 D_s = 3.3e-14 m2/s), which small-particle graphite does not show. Test: D_s x10 and x100, Bruggeman
1.5, R 2.5 / 5 um. If the hypothesis is right, the 54/4C and 102/1C onsets converge. If they don't, it's wrong.
Output: results/cm_bat_r19c_kinetics.json"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_r19_plating_onset as r19
_orig = r19.params
SCALE = 1.0
def params(L, radius, tau):
    p, cmax, b = _orig(L, radius, tau)
    D = p["Positive electrode exchange-current density [A.m-2]"]
    p.update({"Positive electrode exchange-current density [A.m-2]": (lambda *a, D=D, s=SCALE: s * D(*a)) if callable(D) else SCALE * D})
    return p, cmax, b
r19.params = params
rows = []
for s in (10.0, 100.0):
    SCALE = s
    for radius in (2.5e-6, 5e-6):
        for L, c in [(54e-6, 4.0), (102e-6, 1.0), (144e-6, 0.5)]:
            row = {"j0_scale": s, "radius_um": radius * 1e6, "L_um": round(L * 1e6), "crate": c}
            try: row.update(r19.onset(L, c, radius, None))
            except Exception as e: row["error"] = repr(e)[:200]
            rows.append(row); print(row, flush=True)
json.dump({"rows": rows}, open("results/cm_bat_r19c_kinetics.json", "w"), indent=1)
