"""CM-BAT-R21d (design: tessera-relay, 2026-10-02): onset-bracket convergence for the tau 3.4 fit. R21c sampled at 30 s, so
one step = 0.0167 mAh/cm2, the size of the 4.18 vs 4.20 gap. Here tau 3.4 (electrolyte-only, as R21c) at 30/10/5 s; report the
last non-negative and first negative sample (charge + min phi_s-phi_e) as a bracket. Assumes min(phi_s-phi_e) is monotone
in charge near onset (a brief earlier crossing between samples cannot be excluded). Predeclared: if the 5 s bracket moves
onset by > 0.01 mAh/cm2 vs 30 s, the tau 3.4 fit loses a digit. Prediction before running: < 0.01 shift.

Was CM-BAT-R21c: one-factor control for R21b (tessera-relay, 2026-10-01). R21b moved BOTH negative-electrode Bruggeman
coefficients with tau; here the electrode (solid) coefficient stays at the O'Kane default and only the electrolyte
coefficient follows tau. tau 3.4 added to test R21b's interpolated fit directly. Everything else as R21b:

CM-BAT-R21b: remove R21's transfer step. R21 mapped Ma et al. 2022's measured onset (66-73 % SOC at 2 mA/cm2,
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
print("electrode Bruggeman held at", base["Negative electrode Bruggeman coefficient (electrode)"], flush=True)
for tau, per in ((3.4, 30), (3.4, 10), (3.4, 5)):
    p = base.copy()
    p["Negative electrode thickness [m]"] = Ln; p["Positive electrode thickness [m]"] = Lp
    p["Negative electrode porosity"] = eps_n; p["Negative electrode active material volume fraction"] = epsS_n
    bn = 1 - math.log(tau) / math.log(eps_n)
    p["Negative electrode Bruggeman coefficient (electrolyte)"] = bn   # electrode coefficient left at default (R21c)
    I = 20.0 * area
    p["Current function [A]"] = I
    p["Nominal cell capacity [A.h]"] = q_n * area / 1.1
    row = {"tau": tau, "period_s": per, "anode_um": 385, "cathode_um": round(Lp * 1e6), "i_A_m2": 20.0}
    try:
        sol = pybamm.Simulation(pybamm.lithium_ion.DFN(), parameter_values=p,
                                experiment=pybamm.Experiment([f"Charge at {I:.4f} A until 4.2 V"], period=f"{per} seconds"),
                                solver=pybamm.IDAKLUSolver()).solve(initial_soc=0.0)
        d = sol["Negative electrode surface potential difference [V]"].entries
        q = np.abs(sol["Discharge capacity [A.h]"].entries) / area    # Ah/m2
        mins = d.min(axis=0); idx = int(np.argmax(mins < 0)) if (mins < 0).any() else None
        cap = q[-1]
        if idx is not None and idx > 0:
            row["bracket"] = {"last_nonneg_mAh_cm2": round(float(q[idx-1]) / 10, 5), "last_nonneg_min_dphi_V": float(mins[idx-1]),
                              "first_neg_mAh_cm2": round(float(q[idx]) / 10, 5), "first_neg_min_dphi_V": float(mins[idx])}
            # linear zero-crossing inside the bracket
            row["onset_interp_mAh_cm2"] = round(float(q[idx-1] + (q[idx]-q[idx-1]) * mins[idx-1] / (mins[idx-1]-mins[idx])) / 10, 5)
        row.update({"onset_charge_mAh_cm2": round(float(q[idx]) / 10, 4) if idx is not None else None,
                    "onset_pct_of_anode_capacity": round(100 * float(q[idx]) / q_n, 1) if idx is not None else None,
                    "charge_reached_mAh_cm2": round(float(cap) / 10, 2), "anode_capacity_mAh_cm2": round(q_n / 10, 2),
                    "front_node_trip": (int(np.argmin(d[:, idx])) == d.shape[0] - 1) if idx is not None else None})
    except Exception as e:
        row["error"] = repr(e)[:200]
    rows.append(row); print(row, flush=True)
json.dump({"run": "R21d onset bracket at 30/10/5 s, tau 3.4, electrolyte-only (as R21c)", "design": "tessera-relay", "electrode_bruggeman": float(base["Negative electrode Bruggeman coefficient (electrode)"]), "measured_onset_mAh_cm2": 4.2, "rows": rows}, open("results/cm_bat_r21d_bracket.json", "w"), indent=1)
