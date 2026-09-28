"""CM-BAT-R19b: falsify R19's explanation. R19: the DFN breaks the MEASURED self-similarity (54 um/4C plates at 16-33 %
SOC vs 102 um/1C at 50-82 %; measured both 60-70 %). Hypothesis: the model's high-rate onset is set by slow solid
diffusion (Chen2020 D_s = 3.3e-14 m2/s), which small-particle graphite does not show. Test: D_s x10 and x100, Bruggeman
1.5, R 2.5 / 5 um. If the hypothesis is right, the 54/4C and 102/1C onsets converge. If they don't, it's wrong.
Output: results/cm_bat_r19b_diffusivity.json"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_r19_plating_onset as r19
_orig = r19.params
SCALE = 1.0
def params(L, radius, tau):
    p, cmax, b = _orig(L, radius, tau)
    D = p["Positive particle diffusivity [m2.s-1]"]
    p.update({"Positive particle diffusivity [m2.s-1]": (lambda sto, T, D=D, s=SCALE: s * D(sto, T)) if callable(D) else SCALE * D})
    return p, cmax, b
r19.params = params
rows = []
for s in (10.0, 100.0):
    SCALE = s
    for radius in (2.5e-6, 5e-6):
        for L, c in [(54e-6, 4.0), (102e-6, 1.0), (144e-6, 0.5)]:
            row = {"Ds_scale": s, "radius_um": radius * 1e6, "L_um": round(L * 1e6), "crate": c}
            try: row.update(r19.onset(L, c, radius, None))
            except Exception as e: row["error"] = repr(e)[:200]
            rows.append(row); print(row, flush=True)
json.dump({"rows": rows}, open("results/cm_bat_r19b_diffusivity.json", "w"), indent=1)
