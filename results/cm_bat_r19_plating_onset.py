"""CM-BAT-R19: does the DFN predict the MEASURED lithium-plating onset? (specie's question, "does onset shift with
structure/rate", via attempt's extraction of CM-LIT-0171)

Measured (Mijailovic et al., Energy Environ. Sci. 2024, doi:10.1039/D4EE02211D, CM-LIT-0171, extracted by attempt,
quote on record): small-particle graphite half cells, porosity 35 %, matched scaling lambda ~ L^2 * C:
    54 um charged at 4C and 102 um at 1C -> "plating was first observed in half the cells charged to 60 % SOC,
    and observed for all cells charged above 70 % SOC".
The same paper reports self-similar intercalation profiles for 160 um @ 0.5C, 111 um @ 1C, 66 um @ 4C.

Test: PyBaMM DFN half cell (graphite in the working slot, Li counter), Chen2020 graphite + electrolyte.
Plating onset = first time the working-electrode surface potential vs Li, phi_s - phi_e, drops below 0 V anywhere
in the electrode (in practice at the separator side). Reported as SOC = charge passed / theoretical capacity.
Unknowns scanned, not fitted: particle radius 2.5 / 5 um, tortuosity via Bruggeman 1.5 vs tau = 3.
Also run at C/2 for 144 and 160 um (R16's usable-thickness edge region at C/2).
Output: results/cm_bat_r19_plating_onset.json
"""
import json, math, time
import numpy as np
import pybamm

EPS = 0.35
EPS_S = 0.60
CASES = [(54e-6, 4.0), (102e-6, 1.0), (144e-6, 0.5), (160e-6, 0.5)]
RADII = [2.5e-6, 5e-6]
TAU_MODES = {"bruggeman1.5": None, "tau3": 3.0}
xu = pybamm.ParameterValues("Xu2019")


def params(L, radius, tau):
    p = pybamm.ParameterValues("Chen2020")
    for k in [k for k in p.keys() if k.startswith("Negative electrode") or k.startswith("Negative particle")]:
        p.update({k.replace("Negative", "Positive", 1): p[k]}, check_already_exists=False)
    cmax = p["Maximum concentration in negative electrode [mol.m-3]"]
    b = 1.5 if tau is None else 1 - math.log(tau) / math.log(EPS)
    p.update({
        "Maximum concentration in positive electrode [mol.m-3]": cmax,
        "Positive electrode thickness [m]": L, "Positive electrode porosity": EPS,
        "Positive electrode active material volume fraction": EPS_S,
        "Positive electrode Bruggeman coefficient (electrolyte)": b, "Positive particle radius [m]": radius,
        "Separator thickness [m]": 25e-6,
        "Electrode height [m]": 1.0, "Electrode width [m]": 1.0,
        "Number of electrodes connected in parallel to make a cell": 1,
        "Exchange-current density for lithium metal electrode [A.m-2]": xu["Exchange-current density for lithium metal electrode [A.m-2]"],
        "Lithium metal partial molar volume [m3.mol-1]": xu["Lithium metal partial molar volume [m3.mol-1]"],
        "Lower voltage cut-off [V]": -0.5, "Upper voltage cut-off [V]": 1.5,   # cut-off off: we track plating potential, not terminal V
        "Open-circuit voltage at 0% SOC [V]": 1.5, "Open-circuit voltage at 100% SOC [V]": 0.0,
    }, check_already_exists=False)
    return p, cmax, b


def onset(L, crate, radius, tau):
    p, cmax, b = params(L, radius, tau)
    q_theory = EPS_S * L * cmax * 96485 / 3600            # Ah/m2
    I = crate * q_theory
    x0 = 0.02
    p.update({"Initial concentration in positive electrode [mol.m-3]": x0 * cmax, "Current function [A]": I})
    model = pybamm.lithium_ion.DFN({"working electrode": "positive"})
    sim = pybamm.Simulation(model, parameter_values=p, solver=pybamm.IDAKLUSolver(),
                            var_pts={**model.default_var_pts, "x_s": 15, "x_p": 40, "r_p": 30})
    t_end = 3600 * 0.93 / crate                            # up to ~95 % SOC
    sol = sim.solve(np.linspace(0, t_end, 400))
    dphi = sol["Positive electrode surface potential difference [V]"].entries   # (x, t)
    mins = dphi.min(axis=0); t = sol.t
    idx = np.argmax(mins < 0) if (mins < 0).any() else None
    soc = (lambda tt: 100 * (x0 + I * tt / 3600 / q_theory)) if True else None
    return {"onset_SOC_pct": round(float(soc(t[idx])), 1) if idx is not None else None,
            "min_dphi_end_V": round(float(mins[-1]), 4), "bruggeman": round(b, 3),
            "lambda_L2C_um2": round((L * 1e6) ** 2 * crate)}


def main():
    out = {"meta": {"source": "CM-LIT-0171 (Mijailovic 2024) measured onset 60-70 % SOC at 54um/4C and 102um/1C, eps 0.35",
                    "pybamm": pybamm.__version__, "eps": EPS, "eps_s": EPS_S,
                    "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, "rows": []}
    for tname, tau in TAU_MODES.items():
        for radius in RADII:
            for L, c in CASES:
                row = {"L_um": round(L * 1e6), "crate": c, "radius_um": radius * 1e6, "tau_mode": tname}
                try: row.update(onset(L, c, radius, tau))
                except Exception as e: row["error"] = repr(e)[:200]
                out["rows"].append(row); print(row, flush=True)
    json.dump(out, open("results/cm_bat_r19_plating_onset.json", "w"), indent=1)


if __name__ == "__main__":
    main()
