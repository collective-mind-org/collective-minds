"""CM-BAT-R19e (bytes' follow-up on R19d: does uniform porosity + Bruggeman hide a denser front layer?)
Calendering often densifies the electrode surface (separator side). Replace uniform eps 0.35 with a linear gradient,
same mean: front-dense 0.28 -> 0.42 (separator -> current collector) and the reverse. Bruggeman 1.5 applied locally.
Cases 54 um/4C and 102 um/1C, R 5 um. Measured onset: 60-70 % SOC for both. Output: results/cm_bat_r19e_graded.json"""
import json, sys, os
import numpy as np, pybamm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_r19_plating_onset as r19
rows = []
for name, (e_front, e_back) in {"uniform": (0.35, 0.35), "front_dense": (0.28, 0.42), "front_open": (0.42, 0.28)}.items():
    for L, c in ((54e-6, 4.0), (102e-6, 1.0)):
        p, cmax, b = r19.params(L, 5e-6, None)
        Ls = p["Separator thickness [m]"]
        eps = lambda x, Ls=Ls, L=L, ef=e_front, eb=e_back: ef + (eb - ef) * (x - Ls) / L
        p.update({"Positive electrode porosity": eps})
        q = r19.EPS_S * L * cmax * 96485 / 3600; I = c * q
        p.update({"Initial concentration in positive electrode [mol.m-3]": 0.02 * cmax, "Current function [A]": I})
        m = pybamm.lithium_ion.DFN({"working electrode": "positive"})
        try:
            sol = pybamm.Simulation(m, parameter_values=p, solver=pybamm.IDAKLUSolver(),
                                    var_pts={**m.default_var_pts, "x_s": 15, "x_p": 40, "r_p": 30}).solve(np.linspace(0, 3600 * 0.93 / c, 400))
            d = sol["Positive electrode surface potential difference [V]"].entries; mins = d.min(axis=0)
            k = int(np.argmax(mins < 0)) if (mins < 0).any() else None
            row = {"profile": name, "eps_front": e_front, "eps_back": e_back, "L_um": round(L * 1e6), "crate": c,
                   "onset_SOC_pct": round(100 * (0.02 + I * sol.t[k] / 3600 / q), 1) if k is not None else None}
        except Exception as e:
            row = {"profile": name, "L_um": round(L * 1e6), "crate": c, "error": repr(e)[:200]}
        rows.append(row); print(row, flush=True)
json.dump({"rows": rows}, open("results/cm_bat_r19e_graded.json", "w"), indent=1)
