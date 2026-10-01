"""CM-ENERGY-Q01 R06: four DOE 2030 storage technologies against their own break-even bars (German weather, R04 sizing).
Energy-capacity costs and round-trip efficiencies, verbatim from the DOE Storage Innovations 2030 Technology Strategy
Assessments (July 2023), Table 1 of each, all derived from PNNL's 2022 Grid Energy Storage Technology Cost and Performance
Assessment (100-MW, 10-hour plants):
  H2 salt cavern (DOE/OE-0040 p.4): "Storage block costs (salt cavern storage) 6 ... ($/kWh)"; "Round-trip efficiency (RTE) 31%
    Base RTE for a system with 73% electrolyzer efficiency and 51% fuel cell efficiency"
  CAES (DOE/OE-0037 p.4): "Cavern Storage 6.84 Base cavern storage cost ($/kWh)"; "RTE 52% Base RTE"; "references to $/kW and
    $/kWh are related to the power and energy capacities of the CAES system"
  Molten salt + steam turbine (DOE/OE-0038 p.6): "Storage Block Costs 88 Base storage block costs ($/kWhe)"; "Round-trip
    Efficiency (RTE) 44% Base RTE"
  Pumped hydro (DOE/OE-0036 p.4): "Reservoir construction and infrastructure 76 Construction and infrastructure ($/kWh)";
    "Round-trip efficiency 80 Base (%)"
Split of RTE into charge/discharge is OURS (inferred, not in the sources): H2 0.608/0.51 (fuel cell given); CAES and PSH
symmetric sqrt(RTE); molten salt 0.99 resistive charge / 0.444 steam-turbine discharge. Costs are read per kWh of electric
output capacity. Only the energy-scaled line is compared; power-scaled lines are fixed cost (R04).
Usage: python3 results/cm_energy_q01_r06.py"""
import csv, os, json, math
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
TECH = {"H2 salt cavern": (6.0, 0.31 / 0.51, 0.51, 1.0), "CAES cavern": (6.84, math.sqrt(0.52), math.sqrt(0.52), 99),
        "molten salt": (88.0, 0.99, 0.44 / 0.99, 99), "pumped hydro": (76.0, math.sqrt(0.80), math.sqrt(0.80), 99)}
OBs = (1.2, 1.5, 2.0, 3.0); LCOE = (20, 30, 40, 60); out = {}
for name, (cost, ec, ed, cap) in TECH.items():
    S = {OB: min(size_cap(ws, OB, ec, ed, cap) for ws in (0.6, 0.7, 0.8, 0.9)) for OB in OBs}
    Se = {OB: S[OB] * ed for OB in OBs}   # GWh of electric-output capacity
    print(f"{name}: {cost} USD/kWh_e, eta_c {ec:.2f} eta_d {ed:.2f}; GWh_e per GW avg load at OB 1.2/1.5/2/3: {[round(Se[o]) for o in OBs]}")
    rec = {"cost": cost, "eta_c": round(ec, 3), "eta_d": round(ed, 3), "GWh_e": {str(o): round(Se[o]) for o in OBs}, "bars": {}}
    for a, b in ((1.2, 1.5), (1.5, 2.0), (2.0, 3.0)):
        bars = [(b - a) * 8760 * l / (Se[a] - Se[b]) / 0.08 / 1000 for l in LCOE]
        verdict = "store" if cost < min(bars) else "overbuild" if cost > max(bars) else "depends on LCOE"
        print(f"   {a}->{b}: bar USD/kWh_e at LCOE {LCOE}: {[round(x, 1) for x in bars]} -> {verdict}")
        rec["bars"][f"{a}->{b}"] = {"bars": [round(x, 2) for x in bars], "verdict": verdict}
    out[name] = rec
json.dump(out, open(os.path.join(HERE, "CM-ENERGY-Q01-R06.json"), "w"), indent=1)
