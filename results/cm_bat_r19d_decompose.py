"""CM-BAT-R19d (bytes' challenge to R19: is the 4C onset kinetic, or a transport failure masked by j0?)
At the separator-side node, decompose phi_s - phi_e = U(c_s,surf) + eta into equilibrium potential and reaction
overpotential, and record electrolyte concentration, at the moment the model's plating criterion first trips.
Cases: 54 um/4C and 102 um/1C (measured: same onset 60-70 % SOC), R 5 um, Bruggeman 1.5 and tau 3. Chen2020, eps 0.35.
Output: results/cm_bat_r19d_decompose.json"""
import json, sys, os
import numpy as np, pybamm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_r19_plating_onset as r19
rows = []
for tname, tau in (("bruggeman1.5", None), ("tau3", 3.0)):
    for L, c in ((54e-6, 4.0), (102e-6, 1.0)):
        p, cmax, b = r19.params(L, 5e-6, tau)
        q = r19.EPS_S * L * cmax * 96485 / 3600; I = c * q
        p.update({"Initial concentration in positive electrode [mol.m-3]": 0.02 * cmax, "Current function [A]": I})
        m = pybamm.lithium_ion.DFN({"working electrode": "positive"})
        sol = pybamm.Simulation(m, parameter_values=p, solver=pybamm.IDAKLUSolver(),
                                var_pts={**m.default_var_pts, "x_s": 15, "x_p": 40, "r_p": 30}).solve(np.linspace(0, 3600 * 0.93 / c, 400))
        d = sol["Positive electrode surface potential difference [V]"].entries
        U = sol["Positive electrode open-circuit potential [V]"].entries
        eta = sol["Positive electrode reaction overpotential [V]"].entries
        ce = sol["Positive electrolyte concentration [mol.m-3]"].entries
        mins = d.min(axis=0); k = int(np.argmax(mins < 0)) if (mins < 0).any() else len(mins) - 1
        j = 0   # x index 0 = separator side of the working electrode in the half-cell geometry
        ix = int(np.argmin(d[:, k]))
        row = {"L_um": round(L * 1e6), "crate": c, "tau_mode": tname,
               "onset_SOC_pct": round(100 * (0.02 + I * sol.t[k] / 3600 / q), 1),
               "at_onset_node_index": ix, "n_nodes": d.shape[0],
               "U_V": round(float(U[ix, k]), 4), "eta_V": round(float(eta[ix, k]), 4),
               "ce_node": round(float(ce[ix, k]), 1), "ce_min_electrode": round(float(ce[:, k].min()), 1),
               "ce_init": 1000.0}
        rows.append(row); print(row, flush=True)
json.dump({"rows": rows}, open("results/cm_bat_r19d_decompose.json", "w"), indent=1)
