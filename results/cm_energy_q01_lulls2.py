"""CM-ENERGY-Q01 R02: R01's overbuild-storage curve with round-trip losses and with pooling across countries.
Same data (OPSD 2020-10-06, 2015-2019). Losses: storage charged with surplus x eta_rt (all loss put on charging), capacity
= largest cumulative deficit in delivered energy. Pooling: DE, DK, GB, IT (countries with complete load + wind + solar
profiles 2015-2019 in this file); pooled load = sum; pooled wind/solar profile = load-weighted mean of national profiles
(i.e. generation spread in proportion to demand, perfect transmission). Usage: python3 results/cm_energy_q01_lulls2.py"""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "energy_opsd", "ts60.csv")
C = ["DE"]   # pooling deferred: in this OPSD file only DE has wind+solar profiles 2015-2019 (others: load only); needs e.g. Renewables.ninja profiles
rows = []
with open(F) as f:
    for row in csv.DictReader(f):
        if not ("2015-01-01" <= row["utc_timestamp"][:10] <= "2019-12-31"): continue
        try: rows.append({c: (float(row[f"{c}_load_actual_entsoe_transparency"]), float(row[f"{c}_wind_profile"]), float(row[f"{c}_solar_profile"])) for c in C})
        except (ValueError, KeyError): continue
print(f"{len(rows)} hours with all of {C}")
def series(cs):
    Lm = {c: sum(r[c][0] for r in rows) / len(rows) for c in cs}; tot = sum(Lm.values())
    L = [sum(r[c][0] for c in cs) for r in rows]
    W = [sum(r[c][1] * Lm[c] for c in cs) / tot for r in rows]; S = [sum(r[c][2] * Lm[c] for c in cs) / tot for r in rows]
    return L, W, S
def storage(L, W, S, w_share, OB, eta):
    n = len(L); Lm = sum(L) / n; Wm = sum(W) / n; Sm = sum(S) / n
    kw = OB * w_share * Lm / Wm; ks = OB * (1 - w_share) * Lm / Sm; level = worst = 0.0
    for l, w, s in zip(L, W, S):
        net = kw * w + ks * s - l
        level = min(0.0, level + (net * eta if net > 0 else net)); worst = min(worst, level)
    return -worst / Lm
out = {}
for name, cs in (("DE alone", ["DE"]),):
    L, W, S = series(cs)
    for eta, lab in ((1.0, "lossless"), (0.85, "battery 85%"), (0.40, "hydrogen 40%")):
        line = []
        for OB in (1.2, 1.5, 2.0, 3.0):
            h = min(storage(L, W, S, ws, OB, eta) for ws in (0.6, 0.7, 0.8, 0.9)); line.append(round(h)); out[f"{name}|{lab}|{OB}"] = round(h)
        print(f"{name:20s} {lab:13s} storage GWh per GW avg load at overbuild 1.2/1.5/2/3: {line}")
import json; json.dump(out, open(os.path.join(HERE, "CM-ENERGY-Q01-R02.json"), "w"), indent=1)
