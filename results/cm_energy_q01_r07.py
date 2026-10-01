"""CM-ENERGY-Q01-R07: does Germany have the salt caverns for the R05/R06 design (2x overbuild + ~5 days of H2)?
Need (R05/R06): 123-124 GWh_e of output capacity per GW of mean load; H2 store = GWh_e / eta_d (0.51, DOE fuel cell)
= ~243 GWh_H2 per GW. Germany mean load assumed 53 GW (~465 TWh/yr net consumption; ASSUMPTION, not sourced here).
Sources (quoted in problems.md / the R07 write-up):
  - Caglayan et al. 2020, Int J Hydrogen Energy, doi:10.1016/j.ijhydene.2019.12.161 (preprint 10.20944/preprints201910.0187.v1
    abstract): "Germany has the highest technical storage potential, with a value of 9.4 PWhH2, located onshore only".
  - LBEG, Untertage-Gasspeicherung in Deutschland (Stand 1.1.2024; Erdoel Erdgas Kohle 141(2), 2025): 22.7 bn m3 (Vn)
    working gas; 270 individual caverns; caverns hold 62 % of working gas.
Conversion NG -> H2 in the same cavern and pressure window: moles scale by Z_CH4/Z_H2 (~0.75-0.85 at 60-180 bar, ~45 C;
textbook compressibilities, ASSUMPTION), energy by LHV (H2 33.33 kWh/kg). Pure arithmetic, no simulation."""
import json
load_GW, need_e_per_GW, eta_d = 53.0, 123.5, 0.51
need_e = load_GW * need_e_per_GW / 1000            # TWh_e of output
need_h2 = need_e / eta_d                            # TWh_H2 (LHV)
tech_potential = 9400.0                             # TWh_H2, Caglayan (Germany, onshore)
cav_ng = 0.62 * 22.7e9                              # m3 (Vn) working gas in caverns
out = {"need_TWh_e": round(need_e, 2), "need_TWh_H2": round(need_h2, 1),
       "share_of_technical_potential_pct": round(100 * need_h2 / tech_potential, 2),
       "existing_caverns": 270, "existing_cavern_working_gas_bn_m3": round(cav_ng / 1e9, 1), "by_Z_ratio": {}}
for zr in (0.75, 0.78, 0.85):
    h2_TWh = cav_ng / 0.022414 * zr * 2.016e-3 * 33.33 / 1e9
    per_cav = 1000 * h2_TWh / 270
    out["by_Z_ratio"][str(zr)] = {"existing_stock_as_H2_TWh": round(h2_TWh, 1), "GWh_H2_per_cavern": round(per_cav),
                                  "need_as_share_of_existing_stock_pct": round(100 * need_h2 / h2_TWh),
                                  "new_caverns_needed": round(1000 * need_h2 / per_cav)}
print(json.dumps(out, indent=1))
json.dump(out, open("results/CM-ENERGY-Q01-R07.json", "w"), indent=1)
