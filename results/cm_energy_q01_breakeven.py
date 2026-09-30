"""CM-ENERGY-Q01 R03: when is overbuilding wind/solar cheaper than storage? Parametric, no disputed cost inputs.
From R01 (lossless, best wind share, German 2015-2019): storage per GW of average load S(OB) at overbuild OB. Moving from
OB_a to OB_b adds (OB_b - OB_a) x 8,760 GWh/yr of generation per GW of average load (its cost = that x LCOE, whether or not
the extra is curtailed) and saves S(OB_a) - S(OB_b) GWh of storage capacity. Break-even storage capital cost (per kWh of
capacity) = annual extra generation cost / storage saved / CRF; CRF 0.08 (~20 y at 6 %). If storage capacity costs MORE
than this, overbuild; LESS, store. Usage: python3 results/cm_energy_q01_breakeven.py"""
S = {1.0: 1047, 1.2: 278, 1.5: 164, 2.0: 122, 3.0: 59}   # GWh per GW avg load, R01
CRF = 0.08
steps = [(1.0, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 3.0)]
print(f"{'step':>10} {'storage saved GWh':>18} | break-even storage capex, USD per kWh of capacity, at wind/solar LCOE (USD/MWh):")
print(f"{'':>10} {'':>18} | " + "  ".join(f"{l:>6}" for l in (20, 30, 40, 60)))
for a, b in steps:
    saved = S[a] - S[b]; extra_gwh = (b - a) * 8760
    row = [(extra_gwh * 1e6 * l / 1000) / (saved * 1e6) / CRF for l in (20, 30, 40, 60)]   # USD / kWh capacity
    print(f"{a:>4}->{b:<4}  {saved:>18} | " + "  ".join(f"{v:6.0f}" for v in row))
