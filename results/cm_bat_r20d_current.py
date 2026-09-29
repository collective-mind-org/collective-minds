"""CM-BAT-R20d (bytes: does the near-starved anode back at lambda 1.0 trigger premature plating?)
Full cell (O'Kane DFN), tau 1.8, CC C/2, lambda 1.0 and 1.2. At plating onset: where does the reaction current go?
Fraction of anode interfacial current in the front third (separator side) vs back third (collector side), c_e at the
back, and whether phi_s - phi_e ever goes negative at the back. Output: results/cm_bat_r20d_current.json"""
import json, math
import numpy as np, pybamm
base = pybamm.ParameterValues("OKane2022")
area = base["Electrode height [m]"] * base["Electrode width [m]"] * base["Number of electrodes connected in parallel to make a cell"]
Q = base["Nominal cell capacity [A.h]"]; L0 = base["Negative electrode thickness [m]"]; eps = base["Negative electrode porosity"]
kappa = float(base["Electrolyte conductivity [S.m-1]"](pybamm.Scalar(1000.0), pybamm.Scalar(298.15)).evaluate()); K = 0.08; tau = 1.8
rows = []
for lam in (0.6, 1.0, 1.2):
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
    j = sol["Negative electrode interfacial current density [A.m-2]"].entries
    ce = sol["Negative electrolyte concentration [mol.m-3]"].entries
    mins = d.min(axis=0); kk = int(np.argmax(mins < 0)) if (mins < 0).any() else len(mins) - 1
    n = d.shape[0]; third = n // 3
    jt = np.abs(j[:, kk]); tot = jt.sum()
    back_neg = bool((d[:third, :] < 0).any())
    rows.append({"lambda": lam, "k": round(k, 3), "onset_SOC_pct": round(100 * abs(sol["Discharge capacity [A.h]"].entries[kk]) / (Q * k), 1),
                 "current_front_third_pct": round(100 * jt[-third:].sum() / tot, 1), "current_back_third_pct": round(100 * jt[:third].sum() / tot, 1),
                 "ce_back": round(float(ce[0, kk]), 1), "ce_front": round(float(ce[-1, kk]), 1),
                 "dphi_back_V": round(float(d[0, kk]), 4), "dphi_front_V": round(float(d[-1, kk]), 4),
                 "back_ever_negative_during_charge": back_neg})
    print(rows[-1], flush=True)
json.dump({"tau": tau, "rows": rows}, open("results/cm_bat_r20d_current.json", "w"), indent=1)
