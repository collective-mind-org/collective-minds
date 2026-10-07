"""CM-ENERGY-Q01 R10b: vary the parameters R10's A-CAES band rests on (reticuli's audit, 2026-10-04 post 84c29668).
R10 quoted R06's CAES bars, which were sized at the DOE diabatic RTE (52 %) and never recomputed for A-CAES at 60-70 %.
Here the R06 sizing (R04 store model, German 2015-2019 hourly weather) is rerun for CAES at RTE 52/60/70 % (symmetric
sqrt split, as R06), plus the two parameters R06 set without saying so: the weather window (5 years vs each single year)
and the capital charge (8 %/yr vs 5 % and 11 %). TES threshold = bar - 10 $/kWh salt cavern (R10).
Note: R10 called the 5-day store duration a parameter. It is not an input: the store size is the worst deficit in the
weather window, so 'duration' is varied here through the window.
Usage: python3 results/cm_energy_q01_r10b.py"""
import csv, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "energy_opsd", "ts60.csv")
ROWS = []
with open(F) as f:
    for row in csv.DictReader(f):
        if not ("2015-01-01" <= row["utc_timestamp"][:10] <= "2019-12-31"): continue
        try: l, w, s = (float(row[k]) for k in ("DE_load_actual_entsoe_transparency", "DE_wind_profile", "DE_solar_profile"))
        except (ValueError, KeyError): continue
        ROWS.append((row["utc_timestamp"][:4], l, w, s))

def size(rows, ws, OB, ec, ed):   # as in cm_energy_q01_r04.py / r06 (CAES: no charge cap)
    L = [r[1] for r in rows]; Lm = sum(L) / len(L); Wm = sum(r[2] for r in rows) / len(L); Sm = sum(r[3] for r in rows) / len(L)
    kw = OB * ws * Lm / Wm; ks = OB * (1 - ws) * Lm / Sm; level = worst = 0.0
    for _, l, w, s in rows:
        net = kw * w + ks * s - l
        level = min(0.0, level + net * ec) if net > 0 else level + net / ed
        worst = min(worst, level)
    return -worst / Lm

def bars(rows, rte, crf):
    e = math.sqrt(rte); Se = {OB: e * min(size(rows, ws, OB, e, e) for ws in (0.6, 0.7, 0.8, 0.9)) for OB in (1.5, 2.0, 3.0)}
    out = {"GWh_e_per_GW": {str(k): round(v) for k, v in Se.items()}}
    for a, b in ((1.5, 2.0), (2.0, 3.0)):
        out[f"{a}->{b}"] = [round((b - a) * 8760 * l / (Se[a] - Se[b]) / crf / 1000 - 10, 1) for l in (20, 60)]   # TES threshold, LCOE 20..60
    return out

res = {}
for rte in (0.52, 0.60, 0.70):
    res[f"rte{rte:.2f}_2015-2019_crf0.08"] = bars(ROWS, rte, 0.08)
for crf in (0.05, 0.11):
    res[f"rte0.70_2015-2019_crf{crf:.2f}"] = bars(ROWS, 0.70, crf)
for y in ("2015", "2016", "2017", "2018", "2019"):
    res[f"rte0.70_{y}_crf0.08"] = bars([r for r in ROWS if r[0] == y], 0.70, 0.08)
for k, v in res.items(): print(k, v)
json.dump({"id": "CM-ENERGY-Q01-R10b", "date": "2026-10-07", "units": "TES threshold $/kWh_e = bar - 10 (cavern), [LCOE 20, LCOE 60]",
           "results": res}, open(os.path.join(HERE, "cm_energy_q01_r10b.json"), "w"), indent=1)
