"""CM-BAT-R20e: the j0 caveat on R16/R20 (logged in REVISIONS after R19c: 'R16's edge carries an intercalation
exchange-current caveat R17 never scanned'). Does the lambda collapse (R20b: lambda 0.6 -> ~70 % SOC onset,
lambda 1.0 -> ~35 %) hold if the graphite exchange-current density is x0.5 or x2? O'Kane DFN, CC C/2 from 0 %,
tau 1.2 and 3.0 at lambda 0.6 and 1.0. Output: results/cm_bat_r20e_j0.json"""
import json, math
import numpy as np, pybamm
base = pybamm.ParameterValues("OKane2022")
area = base["Electrode height [m]"] * base["Electrode width [m]"] * base["Number of electrodes connected in parallel to make a cell"]
Q = base["Nominal cell capacity [A.h]"]; L0 = base["Negative electrode thickness [m]"]; eps = base["Negative electrode porosity"]
kappa = float(base["Electrolyte conductivity [S.m-1]"](pybamm.Scalar(1000.0), pybamm.Scalar(298.15)).evaluate()); K = 0.08
j0 = base["Negative electrode exchange-current density [A.m-2]"]
rows = []
for s in (0.5, 1.0, 2.0):
    for lam in (0.6, 1.0):
        for tau in (1.2, 3.0):
            k = math.sqrt(lam * K * kappa * eps / tau / (0.5 * Q / area * L0))
            p = base.copy()
            for side in ("Positive", "Negative"):
                p[f"{side} electrode thickness [m]"] = base[f"{side} electrode thickness [m]"] * k
                e = base[f"{side} electrode porosity"]; b = 1 - math.log(tau) / math.log(e)
                p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
            p["Nominal cell capacity [A.h]"] = Q * k
            p["Negative electrode exchange-current density [A.m-2]"] = (lambda *a, f=j0, s=s: s * f(*a)) if callable(j0) else s * j0
            row = {"j0_scale": s, "lambda": lam, "tau": tau, "k": round(k, 3)}
            try:
                sol = pybamm.Simulation(pybamm.lithium_ion.DFN(), parameter_values=p, experiment=pybamm.Experiment(["Charge at C/2 until 4.2 V"], period="30 seconds"),
                                        solver=pybamm.IDAKLUSolver()).solve(initial_soc=0.0)
                d = sol["Negative electrode surface potential difference [V]"].entries; q = np.abs(sol["Discharge capacity [A.h]"].entries)
                mins = d.min(axis=0); idx = int(np.argmax(mins < 0)) if (mins < 0).any() else None
                row["onset_SOC_pct"] = round(100 * q[idx] / (Q * k), 1) if idx is not None else None
            except Exception as e:
                row["error"] = repr(e)[:150]
            rows.append(row); print(row, flush=True)
json.dump({"rows": rows}, open("results/cm_bat_r20e_j0.json", "w"), indent=1)
