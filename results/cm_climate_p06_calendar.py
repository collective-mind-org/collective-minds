"""CM-CLIMATE-P06 R09: a drain calendar anyone can use. For each of the 22 fitted sites (R01), compare fixed calendars with the
site's own best single drain, as CH4 cut vs continuous flooding (Souza et al. 2021 model; 5-day mild drains):
  A 'one mid drain'   : day 40
  B 'one late-ish'    : day 50
  C 'early + mid'     : day 16 and day 40
  D 'early only'      : day 16
Yield guard (not modelled here): mild drying only (field water no lower than 15 cm below surface / soil >= -20 kPa: no
significant yield loss, Carrijo et al. 2017, audited CM-LIT-0620); Islam 2018 and Tran 2017 report early+mid drainage
without yield loss. Usage: .venv/bin/python results/cm_climate_p06_calendar.py"""
import glob, json, os
import numpy as np
import cm_climate_p06_souza as S
CAL = {"A day 40": [(40.0, 5.0)], "B day 50": [(50.0, 5.0)], "C days 16+40": [(16.0, 5.0), (40.0, 5.0)], "D day 16": [(16.0, 5.0)]}
rows = []
for path in sorted(glob.glob(os.path.join(S.DATA, "Data_*.csv"))):
    p = S.load(path)
    if p["name"].startswith("Median"): continue
    x, r2, _ = S.fit(p); T = max(p["t"][-1], 100.0); cf = S.total(*S.simulate(p, x, T, []))
    best = max((1 - S.total(*S.simulate(p, x, T, [(d, 5.0)])) / cf, d) for d in np.arange(3.0, T - 8, 1.0))
    r = dict(site=p["name"], OA=p["C0"] > 0, best_single=round(best[0], 3), best_day=best[1])
    for k, dr in CAL.items(): r[k] = round(1 - S.total(*S.simulate(p, x, T, dr)) / cf, 3)
    rows.append(r)
for oa, lab in ((True, "WITH straw/manure"), (False, "WITHOUT amendment")):
    g = [r for r in rows if r["OA"] == oa]
    print(f"\n{lab} (n={len(g)}): site-best single drain {np.mean([r['best_single'] for r in g]):.0%} on day {np.mean([r['best_day'] for r in g]):.0f} ± {np.std([r['best_day'] for r in g]):.0f}")
    for k in CAL:
        v = [r[k] for r in g]; frac = [r[k] / r["best_single"] for r in g if r["best_single"] > 0]
        print(f"  {k:14s} cut {np.mean(v):.0%} (range {min(v):.0%}…{max(v):.0%});  = {np.mean(frac):.0%} of site-best single")
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CM-CLIMATE-P06-R09-calendar.json"), "w"), indent=1)
