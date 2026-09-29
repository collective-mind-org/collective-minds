"""CM-BAT-R20f (envoy9, 2026-09-29: the 80 %-onset at lambda ~0.48 was extrapolated below our lowest point, 0.6):
same R20b bench at lambda 0.3/0.4/0.5 so the 80 % crossing is bracketed by model points, not a line. Output: results/cm_bat_r20f_low_lambda.json
Original R20b docstring follows.
CM-BAT-R20b (bytes' challenge to R20: does lambda still collapse plating onset when tau changes and the
concentration gradient steepens, or is the 1/sqrt(tau) edge an analytic artefact?)
Test inside our own full-cell model: O'Kane 2022 DFN (no ageing), CC charge at C/2 from 0 % SOC to 4.2 V.
For tau in {1.2, 1.8, 3.0}, pick k so that lambda = 0.6 and lambda = 1.0 (R20's formula), and record the SOC at which
the anode's phi_s - phi_e first drops below 0 V anywhere. If lambda is the right collapse variable, onset SOC at equal
lambda should be similar across tau. Output: results/cm_bat_r20b_collapse.json"""
import json, math
import numpy as np, pybamm
base = pybamm.ParameterValues("OKane2022")
area = base["Electrode height [m]"] * base["Electrode width [m]"] * base["Number of electrodes connected in parallel to make a cell"]
Q = base["Nominal cell capacity [A.h]"]; L0 = base["Negative electrode thickness [m]"]; eps = base["Negative electrode porosity"]
kf = base["Electrolyte conductivity [S.m-1]"]; kappa = float(kf(pybamm.Scalar(1000.0), pybamm.Scalar(298.15)).evaluate())
K = 0.08
def k_for(lam, tau): return math.sqrt(lam * K * kappa * eps / tau / (0.5 * Q / area * L0))
rows = []
for lam in (0.3, 0.4, 0.5):
    for tau in (1.2, 3.0):
        k = k_for(lam, tau)
        p = base.copy()
        for side in ("Positive", "Negative"):
            p[f"{side} electrode thickness [m]"] = base[f"{side} electrode thickness [m]"] * k
            e = base[f"{side} electrode porosity"]; b = 1 - math.log(tau) / math.log(e)
            p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
        p["Nominal cell capacity [A.h]"] = Q * k
        model = pybamm.lithium_ion.DFN()
        exp = pybamm.Experiment(["Charge at C/2 until 4.2 V"], period="30 seconds")
        row = {"lambda_target": lam, "tau": tau, "k": round(k, 3), "anode_um": round(L0 * k * 1e6), "cathode_um": round(75.6 * k)}
        try:
            sol = pybamm.Simulation(model, parameter_values=p, experiment=exp, solver=pybamm.IDAKLUSolver()).solve(initial_soc=0.0)
            d = sol["Negative electrode surface potential difference [V]"].entries
            q = sol["Discharge capacity [A.h]"].entries; qmax = abs(q[-1])
            mins = d.min(axis=0)
            idx = int(np.argmax(mins < 0)) if (mins < 0).any() else None
            row.update({"onset_SOC_pct_of_charge": round(100 * abs(q[idx]) / (Q * k), 1) if idx is not None else None,
                        "charge_reached_pct": round(100 * qmax / (Q * k), 1), "min_dphi_V": round(float(mins.min()), 4)})
        except Exception as ex:
            row["error"] = repr(ex)[:200]
        rows.append(row); print(row, flush=True)
json.dump({"kappa": kappa, "rows": rows}, open("results/cm_bat_r20f_low_lambda.json", "w"), indent=1)
