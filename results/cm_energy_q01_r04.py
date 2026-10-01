"""CM-ENERGY-Q01 R04: does DISCHARGE efficiency matter, and does storage power (GW) move R03's break-even?
R02 put all round-trip loss on charging (qualified 2026-10-01 against Sepulveda et al. 2021, who rank discharge efficiency
among the most important parameters). Here: charge eta_c (surplus x eta_c enters the store) and discharge eta_d (a deficit
d draws d / eta_d from the store), same German data and sizing as R01/R02 (OPSD 2020-10-06, 2015-2019, sequent peak,
best wind share of 0.6-0.9). Also reports the discharge power needed (peak deficit) and charge power used (peak stored
surplus), in GW per GW of average load, uncapped. Usage: python3 results/cm_energy_q01_r04.py"""
import csv, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "energy_opsd", "ts60.csv")
L, W, S = [], [], []
with open(F) as f:
    for row in csv.DictReader(f):
        if not ("2015-01-01" <= row["utc_timestamp"][:10] <= "2019-12-31"): continue
        try: l, w, s = (float(row[k]) for k in ("DE_load_actual_entsoe_transparency", "DE_wind_profile", "DE_solar_profile"))
        except (ValueError, KeyError): continue
        L.append(l); W.append(w); S.append(s)
n = len(L); Lm = sum(L) / n; Wm = sum(W) / n; Sm = sum(S) / n
print(f"{n} hours")
def size(ws, OB, ec, ed):
    kw = OB * ws * Lm / Wm; ks = OB * (1 - ws) * Lm / Sm; level = worst = pd = pc = 0.0
    for l, w, s in zip(L, W, S):
        net = kw * w + ks * s - l
        if net > 0:
            room = -level; inp = min(net * ec, room); level += inp; pc = max(pc, inp / ec)
        else:
            level += net / ed; pd = max(pd, -net)
        worst = min(worst, level)
    return -worst / Lm, pd / Lm, pc / Lm
cases = [("lossless", 1.0, 1.0), ("battery 85% on charge", 0.85, 1.0), ("battery 85% on discharge", 1.0, 0.85),
         ("battery 85% split", 0.922, 0.922),
         ("H2 40% on charge", 0.40, 1.0), ("H2 40% on discharge", 1.0, 0.40), ("H2 40% split 0.7x0.57", 0.70, 0.571)]
OBs = (1.2, 1.5, 2.0, 3.0); out = {}
for lab, ec, ed in cases:
    res = []
    for OB in OBs:
        best = min((size(ws, OB, ec, ed) + (ws,) for ws in (0.6, 0.7, 0.8, 0.9)), key=lambda t: t[0])
        res.append(best); out[f"{lab}|{OB}"] = {"GWh": round(best[0]), "P_dis": round(best[1], 2), "P_chg": round(best[2], 2), "wind_share": best[3]}
    print(f"{lab:26s} GWh/GW at OB 1.2/1.5/2/3: {[round(r[0]) for r in res]}   P_dis {[round(r[1],2) for r in res]}  P_chg {[round(r[2],2) for r in res]}")
json.dump(out, open(os.path.join(HERE, "CM-ENERGY-Q01-R04.json"), "w"), indent=1)

# Charge-power cap (electrolyser / charger size), H2 split and battery split: GW of surplus absorbed per GW of average load.
def size_cap(ws, OB, ec, ed, cap):
    kw = OB * ws * Lm / Wm; ks = OB * (1 - ws) * Lm / Sm; level = worst = 0.0; capL = cap * Lm
    for l, w, s in zip(L, W, S):
        net = kw * w + ks * s - l
        level = min(0.0, level + min(net, capL) * ec) if net > 0 else level + net / ed
        worst = min(worst, level)
    return -worst / Lm
for lab, ec, ed in (("battery 85% split", 0.922, 0.922), ("H2 40% split 0.7x0.57", 0.70, 0.571)):
    for cap in (0.5, 1.0, 1.5, 99):
        r = [round(min(size_cap(ws, OB, ec, ed, cap) for ws in (0.6, 0.7, 0.8, 0.9))) for OB in OBs]
        out[f"{lab}|cap{cap}"] = r
        print(f"{lab:26s} charge cap {cap:>4} GW/GW: GWh/GW at OB 1.2/1.5/2/3: {r}")
json.dump(out, open(os.path.join(HERE, "CM-ENERGY-Q01-R04.json"), "w"), indent=1)
