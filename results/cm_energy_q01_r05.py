"""CM-ENERGY-Q01 R05: R04's sizing with the DOE 2030 salt-cavern hydrogen figures, and the break-even bar they must meet.
Source (verbatim, DOE/OE-0040 Hydrogen Storage Technology Strategy Assessment, July 2023, Table 1, p. 4, values from PNNL
2022 Grid Energy Storage Technology Cost and Performance Assessment, 100-MW 10-hour bidirectional salt cavern):
"Round-trip efficiency (RTE) 31% Base RTE for a system with 73% electrolyzer efficiency and 51% fuel cell efficiency";
"Storage block costs (salt cavern storage) 6 Base storage block costs for salt cavern storage systems ($/kWh)".
Here eta_d = 0.51 (fuel cell) and eta_c = 0.31 / 0.51 = 0.608 (electrolyser + compression, so that RTE = 31 %).
Usage: python3 results/cm_energy_q01_r05.py"""
import csv, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "energy_opsd", "ts60.csv")
L, W, S_ = [], [], []
with open(F) as f:
    for row in csv.DictReader(f):
        if not ("2015-01-01" <= row["utc_timestamp"][:10] <= "2019-12-31"): continue
        try: l, w, s = (float(row[k]) for k in ("DE_load_actual_entsoe_transparency", "DE_wind_profile", "DE_solar_profile"))
        except (ValueError, KeyError): continue
        L.append(l); W.append(w); S_.append(s)
n = len(L); Lm = sum(L) / n; Wm = sum(W) / n; Sm = sum(S_) / n
def size_cap(ws, OB, ec, ed, cap):   # as in cm_energy_q01_r04.py
    kw = OB * ws * Lm / Wm; ks = OB * (1 - ws) * Lm / Sm; level = worst = 0.0; capL = cap * Lm
    for l, w, s in zip(L, W, S_):
        net = kw * w + ks * s - l
        level = min(0.0, level + min(net, capL) * ec) if net > 0 else level + net / ed
        worst = min(worst, level)
    return -worst / Lm
OBs = (1.2, 1.5, 2.0, 3.0); ec, ed = 0.31 / 0.51, 0.51; out = {}
for cap in (1.0, 99):
    S = {OB: min(size_cap(ws, OB, ec, ed, cap) for ws in (0.6, 0.7, 0.8, 0.9)) for OB in OBs}
    out[f"cap{cap}"] = {str(k): round(v) for k, v in S.items()}
    print(f"DOE H2 (eta_c {ec:.3f}, eta_d {ed}) charge cap {cap:>4} GW/GW: GWh stored per GW avg load at OB 1.2/1.5/2/3: {[round(S[o]) for o in OBs]}")
    for a, b in ((1.2, 1.5), (1.5, 2.0), (2.0, 3.0)):
        saved = S[a] - S[b]; ex = (b - a) * 8760
        bars = [ex * l / saved / 0.08 / 1000 for l in (20, 30, 40, 60)]   # USD per kWh of stored-H2 capacity
        print(f"   {a}->{b}: break-even USD/kWh stored at LCOE 20/30/40/60: {[round(x, 1) for x in bars]}  (/ eta_d -> per kWh of electric-output capacity: {[round(x / ed, 1) for x in bars]})")
        out[f"cap{cap}|{a}->{b}"] = [round(x, 2) for x in bars]
json.dump(out, open(os.path.join(HERE, "CM-ENERGY-Q01-R05.json"), "w"), indent=1)
