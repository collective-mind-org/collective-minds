"""CM-BAT-R21b: remove R21's transfer step. R21 mapped Ma et al. 2022's measured onset (66-73 % SOC at 2 mA/cm2,
385 um graphite, eps 0.4) through our O'Kane full-cell lambda collapse. Here we simulate Ma's anode directly:
O'Kane 2022 DFN parameters, anode 385 um at porosity 0.4 (active fraction from Ma's 17 mg/cm2 loading, ~0.195), cathode thickened to N/P ~ 1.1, CC charge at 2 mA/cm2 (20 A/m2) from 0 % to 4.2 V, tortuosity scanned.
Onset = anode phi_s - phi_e < 0 anywhere; SOC = charge passed / anode-limited capacity. Output: results/cm_bat_r21b_direct.json"""
import json, math
import numpy as np, pybamm
base = pybamm.ParameterValues("OKane2022")
area = base["Electrode height [m]"] * base["Electrode width [m]"] * base["Number of electrodes connected in parallel to make a cell"]
Ln, Lp = 385e-6, None
eps_n = 0.4
epsS_n0, eps_n0 = base["Negative electrode active material volume fraction"], base["Negative electrode porosity"]
epsS_n = 17e-3 / (2.26 * 385e-4)             # from Ma's loading: 17 mg/cm2 graphite in 385 um (density 2.26 g/cm3) -> ~0.195 (first attempt kept O'Kane's 0.60: 3.4x too much capacity, invalid)
cmax_n = base["Maximum concentration in negative electrode [mol.m-3]"]
q_n = epsS_n * Ln * cmax_n * 96485 / 3600     # Ah/m2 anode theoretical
cmax_p = base["Maximum concentration in positive electrode [mol.m-3]"]; epsS_p = base["Positive electrode active material volume fraction"]
Lp = q_n / 1.1 / (epsS_p * cmax_p * 96485 / 3600 * 0.7)   # cathode sized for N/P ~1.1 at ~70 % usable stoichiometry window
rows = []
for tau in (1.6, 2.0, 2.4, 3.0, 4.3):
    p = base.copy()
    p["Negative electrode thickness [m]"] = Ln; p["Positive electrode thickness [m]"] = Lp
    p["Negative electrode porosity"] = eps_n; p["Negative electrode active material volume fraction"] = epsS_n
    bn = 1 - math.log(tau) / math.log(eps_n)
    p["Negative electrode Bruggeman coefficient (electrolyte)"] = bn; p["Negative electrode Bruggeman coefficient (electrode)"] = bn
    I = 20.0 * area
    p["Current function [A]"] = I
    p["Nominal cell capacity [A.h]"] = q_n * area / 1.1
    row = {"tau": tau, "anode_um": 385, "cathode_um": round(Lp * 1e6), "i_A_m2": 20.0}
    try:
        sol = pybamm.Simulation(pybamm.lithium_ion.DFN(), parameter_values=p,
                                experiment=pybamm.Experiment([f"Charge at {I:.4f} A until 4.2 V"], period="30 seconds"),
                                solver=pybamm.IDAKLUSolver()).solve(initial_soc=0.0)
        d = sol["Negative electrode surface potential difference [V]"].entries
        q = np.abs(sol["Discharge capacity [A.h]"].entries) / area    # Ah/m2
        mins = d.min(axis=0); idx = int(np.argmax(mins < 0)) if (mins < 0).any() else None
        cap = q[-1]
        row.update({"onset_charge_mAh_cm2": round(float(q[idx]) / 10, 2) if idx is not None else None,
                    "onset_pct_of_anode_capacity": round(100 * float(q[idx]) / q_n, 1) if idx is not None else None,
                    "charge_reached_mAh_cm2": round(float(cap) / 10, 2), "anode_capacity_mAh_cm2": round(q_n / 10, 2),
                    "front_node_trip": (int(np.argmin(d[:, idx])) == d.shape[0] - 1) if idx is not None else None})
    except Exception as e:
        row["error"] = repr(e)[:200]
    rows.append(row); print(row, flush=True)
json.dump({"measured": {"onset_mAh_cm2": 4.2, "onset_pct": "66-73", "onset_pct_basis": "Ma 2022 practical capacity: 0.017 g/cm2 x 340-372 mAh/g = 5.78-6.32 mAh/cm2", "onset_pct_of_model_anode_capacity": 62.9, "note": "rows' onset_pct_of_anode_capacity use the model capacity 6.68 mAh/cm2; compare percentages on that basis (62.9), or compare mAh/cm2 directly (the R21b fit tau ~3.4 uses mAh/cm2). Denominator split found by tessera-relay 2026-10-01."}, "rows": rows}, open("results/cm_bat_r21b_direct.json", "w"), indent=1)
