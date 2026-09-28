"""CM-BAT-R18: does the DFN transport model reproduce a measured thick-electrode result?

Target (measured): Billaud et al., Nature Energy 1, 16097 (2016), doi:10.1038/nenergy.2016.97.
~200 um graphite flake electrode, 9.1 mg/cm2 (SI Fig. 7), graphite vs Li metal, LiPF6 EC:DEC.
Magnetic alignment gives "a specific charge up to three times higher ... at a rate of 1C" (abstract).
Through-plane tortuosity factors from FIB-SEM (SI Table 1, z direction):
    aligned      eps 0.32  tau 3.84
    not aligned  eps 0.45  tau 13.95
Prediction under test: the capacity ratio aligned/reference at 1C given ONLY these measured
tortuosities, everything else identical. We set the Bruggeman exponent so eps^b = eps/tau.

Model: PyBaMM DFN half cell (working electrode = graphite mapped into the 'positive' slot,
Li metal counter). Chen2020 graphite + electrolyte (EC:EMC, not EC:DEC). Assumptions we cannot
pin from the paper are scanned: particle radius (flake half-width), separator (25 um polymer vs
260 um glass fibre, typical for lab half cells) and porosity (as measured vs equal).
Output: results/cm_bat_r18_billaud.json
"""
import json, math, sys, time
import pybamm

L = 200e-6
LOADING = 9.1e-2          # kg/m2  (9.1 mg/cm2)
RHO_G = 2260.0            # kg/m3 graphite
EPS_S = LOADING / (RHO_G * L)   # active volume fraction, same for both electrodes (same mass)
ELECTRODES = {"aligned": (0.32, 3.84), "reference": (0.45, 13.95)}
RATES = [0.1, 0.2, 0.5, 1.0, 2.0]
RADII = [5e-6, 10e-6]
SEPARATORS = {"polymer25": (25e-6, 0.47, 1.5), "glassfibre260": (260e-6, 0.90, 1.5)}
POROSITY_MODES = ["as_measured", "equal_0.45"]

xu = pybamm.ParameterValues("Xu2019")


def params(eps, tau, radius, sep):
    p = pybamm.ParameterValues("Chen2020")
    neg = {k: p[k] for k in p.keys() if k.startswith("Negative electrode") or k.startswith("Negative particle")}
    for k, v in neg.items():
        p.update({k.replace("Negative", "Positive", 1): v}, check_already_exists=False)
    cmax = p["Maximum concentration in negative electrode [mol.m-3]"]
    b = 1 - math.log(tau) / math.log(eps)
    sep_L, sep_eps, sep_b = sep
    p.update({
        "Maximum concentration in positive electrode [mol.m-3]": cmax,
        "Positive electrode thickness [m]": L,
        "Positive electrode porosity": eps,
        "Positive electrode active material volume fraction": EPS_S,
        "Positive electrode Bruggeman coefficient (electrolyte)": b,
        "Positive particle radius [m]": radius,
        "Separator thickness [m]": sep_L,
        "Separator porosity": sep_eps,
        "Separator Bruggeman coefficient (electrolyte)": sep_b,
        "Electrode height [m]": 1.0, "Electrode width [m]": 1.0,
        "Number of electrodes connected in parallel to make a cell": 1,
        "Exchange-current density for lithium metal electrode [A.m-2]":
            xu["Exchange-current density for lithium metal electrode [A.m-2]"],
        "Lithium metal partial molar volume [m3.mol-1]": xu["Lithium metal partial molar volume [m3.mol-1]"],
        "Lower voltage cut-off [V]": 0.005, "Upper voltage cut-off [V]": 1.5,
        "Open-circuit voltage at 0% SOC [V]": 1.5, "Open-circuit voltage at 100% SOC [V]": 0.005,
    }, check_already_exists=False)
    return p, cmax, b


def run(eps, tau, radius, sep, crate, direction):
    p, cmax, b = params(eps, tau, radius, sep)
    q_theory = EPS_S * L * cmax * 96485 / 3600          # Ah per m2
    i1c = LOADING * 1e3 * 0.372                          # A/m2 at 1C = 372 mAh/g (paper convention)
    x0 = 0.02 if direction == "lithiation" else 0.90
    p.update({"Initial concentration in positive electrode [mol.m-3]": x0 * cmax,
              "Current function [A]": (1 if direction == "lithiation" else -1) * crate * i1c})
    model = pybamm.lithium_ion.DFN({"working electrode": "positive"})
    ev = {"lithiation": "Minimum voltage [V]", "delithiation": "Maximum voltage [V]"}[direction]
    sim = pybamm.Simulation(model, parameter_values=p, solver=pybamm.IDAKLUSolver(),
                            var_pts={**model.default_var_pts, "x_s": 20, "x_p": 40, "r_p": 30})
    # Chen2020 graphite OCP flattens at ~0.09 V near x=0.9, so equilibrium never reaches 5 mV:
    # cap the window at the usable range x 0.02..0.90 (stop by time) or the voltage cut-off, whichever first.
    t_end = 3600 * (0.88 * q_theory) / (crate * i1c)
    sol = sim.solve([0, t_end])
    q = abs(sol["Discharge capacity [A.h]"].entries[-1])          # Ah per m2
    mass_g = LOADING * 1e3                                            # g per m2
    return {"mAh_per_g": 1000 * q / mass_g, "frac_theory": q / q_theory, "bruggeman": b,
            "cutoff_hit": float(sol.t[-1]) < 0.999 * t_end, "end_V": float(sol["Voltage [V]"].entries[-1]), "t_end_s": float(sol.t[-1])}


def main():
    out = {"meta": {"source": "doi:10.1038/nenergy.2016.97 SI Table 1", "eps_s": EPS_S,
                    "pybamm": pybamm.__version__, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
           "rows": []}
    for pm in POROSITY_MODES:
        for rname, radius in [(f"R{int(r*1e6)}um", r) for r in RADII]:
            for sname, sep in SEPARATORS.items():
                for crate in RATES:
                    for direction in ["lithiation", "delithiation"]:
                        row = {"porosity_mode": pm, "radius": rname, "separator": sname, "crate": crate,
                               "direction": direction}
                        for ename, (eps, tau) in ELECTRODES.items():
                            e = 0.45 if pm == "equal_0.45" else eps
                            try:
                                row[ename] = run(e, tau, radius, sep, crate, direction)
                            except Exception as exc:  # record, don't hide
                                row[ename] = {"error": repr(exc)[:200]}
                        a, r = row["aligned"].get("mAh_per_g"), row["reference"].get("mAh_per_g")
                        row["ratio"] = a / r if a and r else None
                        out["rows"].append(row)
                        print(pm, rname, sname, crate, direction,
                              f"aligned {a and round(a)} ref {r and round(r)} ratio {row['ratio'] and round(row['ratio'], 2)}",
                              flush=True)
    json.dump(out, open("results/cm_bat_r18_billaud.json", "w"), indent=1)


if __name__ == "__main__":
    main()
