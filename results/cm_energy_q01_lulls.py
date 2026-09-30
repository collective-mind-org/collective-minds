"""CM-ENERGY-Q01 R01: how much storage do REAL wind/solar lulls need? The problem statement assumed a 5-day total lull
(120 GWh per GW of average load). Test it on six years of hourly German data (Open Power System Data, time_series
2020-10-06, 60 min, CC BY 4.0; sources ENTSO-E Transparency, netztransparenz.de via OPSD): load, and wind (on+offshore)
and solar capacity-factor profiles. Portfolio: wind + solar profiles scaled so that annual renewable energy = annual
load x overbuild factor OB; wind share w of renewable energy. Storage needed = the largest cumulative deficit over
the whole record (sequent-peak), lossless (upper bound on efficiency, so a lower bound on storage), in GWh per GW of
average load. Usage: python3 results/cm_energy_q01_lulls.py   (needs results/energy_opsd/ts60.csv, see README there)"""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "energy_opsd", "ts60.csv")
L, W, S = [], [], []
with open(F) as f:
    r = csv.DictReader(f)
    for row in r:
        t = row["utc_timestamp"]
        if not ("2015-01-01" <= t[:10] <= "2019-12-31"): continue
        try: l = float(row["DE_load_actual_entsoe_transparency"]); w = float(row["DE_wind_profile"]); s = float(row["DE_solar_profile"])
        except ValueError: continue
        L.append(l); W.append(w); S.append(s)
n = len(L); Lm = sum(L) / n; Wm = sum(W) / n; Sm = sum(S) / n
print(f"{n} complete hours 2015-2019; mean load {Lm/1000:.1f} GW; mean wind CF {Wm:.3f}, solar CF {Sm:.3f}")
def storage(w_share, OB):
    kw = OB * w_share * Lm / Wm; ks = OB * (1 - w_share) * Lm / Sm
    level = peak = 0.0; worst = 0.0; worst_len = cur_len = 0
    for l, w, s in zip(L, W, S):
        net = kw * w + ks * s - l   # MW surplus (+) / deficit (-)
        level = min(0.0, level + net)           # running deficit since last full
        worst = min(worst, level)
        cur_len = cur_len + 1 if level < 0 else 0; worst_len = max(worst_len, cur_len)
    return -worst / Lm, worst_len   # hours of average load, longest deficit run (h)
print(f"{'wind share':>10} {'overbuild':>9} {'storage (GWh per GW avg load)':>30} {'= days of avg load':>18} {'longest deficit run (days)':>27}")
best = {}
for OB in (1.0, 1.2, 1.5, 2.0, 3.0):
    for w_share in (0.6, 0.7, 0.8, 0.9):
        h, run = storage(w_share, OB)
        print(f"{w_share:10.1f} {OB:9.1f} {h:30.0f} {h/24:18.1f} {run/24:27.1f}")
        if OB not in best or h < best[OB][0]: best[OB] = (h, w_share)
print("\nbest mix per overbuild:", {k: (round(v[0]), v[1]) for k, v in best.items()}, " | assumption in CM-ENERGY-Q01: 120 GWh per GW")
