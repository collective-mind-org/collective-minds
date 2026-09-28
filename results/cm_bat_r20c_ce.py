"""CM-BAT-R20c (bytes' follow-up to R20b: at equal lambda, is the separator-side electrolyte depleting at tau 3.0?)
Same cells as R20b at lambda = 0.6 and 1.0 (O'Kane DFN, CC charge C/2 from 0 %). At the moment anode phi_s - phi_e
first drops below 0: electrolyte concentration at the anode/separator interface, minimum in the anode, and where
the trip happens. Output: results/cm_bat_r20c_ce.json"""
import json, math, sys, os
import numpy as np, pybamm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location("r20b", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cm_bat_r20b_collapse.py"))
base = pybamm.ParameterValues("OKane2022")
area = base["Electrode height [m]"] * base["Electrode width [m]"] * base["Number of electrodes connected in parallel to make a cell"]
Q = base["Nominal cell capacity [A.h]"]; L0 = base["Negative electrode thickness [m]"]; eps = base["Negative electrode porosity"]
kappa = float(base["Electrolyte conductivity [S.m-1]"](pybamm.Scalar(1000.0), pybamm.Scalar(298.15)).evaluate())
K = 0.08
rows = []
for lam in (0.6, 1.0):
    for tau in (1.2, 1.8, 3.0):
        k = math.sqrt(lam * K * kappa * eps / tau / (0.5 * Q / area * L0))
        p = base.copy()
        for side in ("Positive", "Negative"):
            p[f"{side} electrode thickness [m]"] = base[f"{side} electrode thickness [m]"] * k
            e = base[f"{side} electrode porosity"]; b = 1 - math.log(tau) / math.log(e)
            p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
        p["Nominal cell capacity [A.h]"] = Q * k
        sol = pybamm.Simulation(pybamm.lithium_ion.DFN(), parameter_values=p, experiment=pybamm.Experiment(["Charge at C/2 until 4.2 V"], period="30 seconds"),
                                solver=pybamm.IDAKLUSolver()).solve(initial_soc=0.0)
        d = sol["Negative electrode surface potential difference [V]"].entries
        ce = sol["Negative electrolyte concentration [mol.m-3]"].entries
        mins = d.min(axis=0); kk = int(np.argmax(mins < 0)) if (mins < 0).any() else len(mins) - 1
        ix = int(np.argmin(d[:, kk])); n = d.shape[0]
        rows.append({"lambda": lam, "tau": tau, "k": round(k, 3),
                     "trip_node": f"{ix}/{n - 1} (0 = current collector side, {n - 1} = separator side)",
                     "ce_sep_interface": round(float(ce[-1, kk]), 1), "ce_min_anode": round(float(ce[:, kk].min()), 1),
                     "ce_min_location_node": int(np.argmin(ce[:, kk]))})
        print(rows[-1], flush=True)
json.dump({"rows": rows}, open("results/cm_bat_r20c_ce.json", "w"), indent=1)
