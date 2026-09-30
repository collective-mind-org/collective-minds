"""CM-CLIMATE-P06 bench v0: does a second (or third) drain beat one well-timed drain, once N2O is counted?
CH4: the Souza et al. 2021 model refitted to its 22 field experiments (results/cm_climate_p06_souza.py, R01).
N2O and yield: literature averages, not a model (v0; replace me):
  - N2O share of a continuously flooded field's warming (CH4+N2O, GWP100), solved from two meta-analysis abstracts:
    Liu et al. 2019 (Agric. Water Manag. 213:1028, doi:10.1016/j.agwat.2018.12.025): mid-season drainage CH4 -52 %, N2O +242 %,
    GWP -47 %  ->  f = 0.017;  Zhao et al. 2024 (GCB, doi:10.1111/gcb.17581): AWD CH4 -51.6 %, N2O +44.0 %, GWP -46.9 %  ->  f = 0.049.
  - Extra N2O per drain event, in units of the flooded field's warming: p = 0.017 x 2.42 = 0.041 (Liu, one drain) as the high
    case, 0.049 x 0.44 = 0.022 (Zhao, whole AWD season, charged per drain) as the low case. Liu: 'increasing drainage times did
    not affect the response of GWP', so charging p per drain is pessimistic for extra drains.
  - Yield: unchanged for 5-day drains (Liu: 'no effect on rice grain yield'; Carrijo 2017 abstract: Mild AWD yields 'not
    significantly reduced'). Souza's caveat applies: logistic growth may not hold under many drains.
Score per site: net warming cut vs continuous flooding, (1-f) * eta_CH4 - n_drains * p. Bar: best single drain.
Usage: .venv/bin/python results/cm_climate_p06_bench.py"""
import glob, itertools, json, os
import numpy as np
import cm_climate_p06_souza as S

L, P_CASES, F = 5.0, {"low p=0.022": 0.022, "high p=0.041": 0.041}, 0.033   # F: mid of 0.017-0.049
def eta(p, x, drains, T):
    cf = S.total(*S.simulate(p, x, T, [])); return (cf - S.total(*S.simulate(p, x, T, drains))) / cf

if __name__ == "__main__":
    out = []
    for path in sorted(glob.glob(os.path.join(S.DATA, "Data_*.csv"))):
        p = S.load(path)
        if p["name"].startswith("Median"): continue
        x, r2, _ = S.fit(p); T = max(p["t"][-1], 100.0); days = np.arange(5.0, T - L, 3.0)
        e1 = max((eta(p, x, [(d, L)], T), d) for d in days)
        e2 = max((eta(p, x, [(a, L), (b, L)], T), a, b) for a, b in itertools.combinations(days, 2) if b - a >= 2 * L)
        e3 = max((eta(p, x, [(a, L), (b, L), (c, L)], T), a, b, c) for a, b, c in itertools.combinations(days[::2], 3) if b - a >= 2 * L and c - b >= 2 * L)
        row = dict(name=p["name"], OA=p["C0"] > 0, R2=round(r2, 2), eta1=round(e1[0], 3), td1=e1[1], eta2=round(e2[0], 3), td2=e2[1:], eta3=round(e3[0], 3), td3=e3[1:])
        for k, pc in P_CASES.items():
            net = [(1 - F) * e - n * pc for n, e in ((1, e1[0]), (2, e2[0]), (3, e3[0]))]
            row[k] = dict(net=[round(v, 3) for v in net], best_n=int(np.argmax(net)) + 1)
        out.append(row)
        print(f"{row['name']:10s} {'OA' if row['OA'] else 'NA'}  CH4 cut: 1 drain {row['eta1']:.2f} (d{row['td1']:.0f})  2 {row['eta2']:.2f}  3 {row['eta3']:.2f}  | best n: low-p {row['low p=0.022']['best_n']}, high-p {row['high p=0.041']['best_n']}", flush=True)
    for k in P_CASES:
        for grp in (False, True):
            g = [r for r in out if r["OA"] == grp]; gain = [r[k]["net"][1] - r[k]["net"][0] for r in g]
            print(f"{k} {'OA' if grp else 'NA'}: second drain adds {np.mean(gain):+.3f} ± {np.std(gain):.3f} net (of flooded-field warming); worth it at {sum(v > 0 for v in gain)}/{len(g)} sites")
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CM-CLIMATE-P06-bench-v0.json"), "w"), indent=1, default=float)
