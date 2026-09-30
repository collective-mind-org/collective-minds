"""CM-CLIMATE-P06 R08: does the Souza et al. 2021 model reproduce the measured TIMING effect?
Within-study designed trials: adding an early drain to the mid-season drain cut CH4 a further 14 % (reduced residue) and 55 %
(full residue) vs mid-season only in the field (Tran et al. 2017, doi:10.1016/j.agee.2017.08.011), and 75-77 % in a straw
growth chamber (Islam et al. 2018, doi:10.1016/j.scitotenv.2017.09.022). Here: each of the 22 fitted sites (R01), mid-season
drain at day 40 alone vs early (day 16) + mid (day 40), drains 5 and 10 days long; extra cut = 1 - E(early+mid) / E(mid).
Usage: .venv/bin/python results/cm_climate_p06_timing.py"""
import glob, json, os
import numpy as np
import cm_climate_p06_souza as S
rows = []
for path in sorted(glob.glob(os.path.join(S.DATA, "Data_*.csv"))):
    p = S.load(path)
    if p["name"].startswith("Median"): continue
    x, r2, _ = S.fit(p); T = max(p["t"][-1], 100.0)
    for L in (5.0, 10.0):
        mid = S.total(*S.simulate(p, x, T, [(40.0, L)])); both = S.total(*S.simulate(p, x, T, [(16.0, L), (40.0, L)]))
        rows.append(dict(site=p["name"], OA=p["C0"] > 0, L=L, extra_cut=round(1 - both / mid, 3)))
for oa in (False, True):
    for L in (5.0, 10.0):
        v = [r["extra_cut"] for r in rows if r["OA"] == oa and r["L"] == L]
        print(f"{'amended' if oa else 'non-amended':12s} drains {L:.0f} d: early drain adds {np.mean(v):.0%} (range {min(v):.0%}…{max(v):.0%}, n={len(v)})")
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CM-CLIMATE-P06-R08-timing.json"), "w"), indent=1)
