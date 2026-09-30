"""CM-BAT-R12d (reticuli's open question on R12c, 2026-09-30): the κ,D×0.5 τ1.8 cell delivers 4.66 of 10 Ah on cycle 1.
Is the charge cut short in the CC phase (4.2 V reached early) or in the CV hold? Five cycles at k=2, C/2, τ {1.2, 1.8},
same parameters as R12c; per cycle, the Ah passed in each step (discharge, CC charge, CV hold).
Usage: ./run_sim.sh results/cm_bat_r12d_cc_cv.py"""
import json, math, os, sys
import pybamm
pybamm.set_logging_level("ERROR")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm_bat_sweep as sw
out = {}
for tau in (1.2, 1.8):
    base = pybamm.ParameterValues("OKane2022"); p = base.copy(); k = 2.0
    for side in ("Positive", "Negative"):
        p[f"{side} electrode thickness [m]"] = base[f"{side} electrode thickness [m]"] * k
        eps = base[f"{side} electrode porosity"]; b = 1 - math.log(tau) / math.log(eps)
        p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
    p["Nominal cell capacity [A.h]"] = base["Nominal cell capacity [A.h]"] * k
    for name in ("Electrolyte conductivity [S.m-1]", "Electrolyte diffusivity [m2.s-1]"):
        v = p[name]; p[name] = (lambda *a, v=v: 0.5 * v(*a)) if callable(v) else 0.5 * v
    opts = {"SEI": "solvent-diffusion limited", "SEI porosity change": "true", "lithium plating": "partially reversible", "lithium plating porosity change": "true",
            "particle mechanics": ("swelling and cracking", "swelling only"), "SEI on cracks": "true"}
    sim = pybamm.Simulation(pybamm.lithium_ion.DFN(opts), parameter_values=p, experiment=pybamm.Experiment([sw.CYCLE(0.5)] * 5), solver=pybamm.IDAKLUSolver())
    sol = sim.solve()
    rows = []
    for i, cyc in enumerate(sol.cycles, 1):
        ah = lambda st: float(abs(st["Discharge capacity [A.h]"].entries[-1] - st["Discharge capacity [A.h]"].entries[0]))
        hrs = lambda st: float((st["Time [s]"].entries[-1] - st["Time [s]"].entries[0]) / 3600)
        dis, cc, cv = cyc.steps[0], cyc.steps[2], cyc.steps[3]
        rows.append({"cycle": i, "discharge_Ah": ah(dis), "cc_charge_Ah": ah(cc), "cc_h": hrs(cc), "cv_charge_Ah": ah(cv), "cv_h": hrs(cv),
                     "V_end_discharge": float(dis["Voltage [V]"].entries[-1])})
        print(f"tau {tau} cycle {i}: discharge {rows[-1]['discharge_Ah']:.2f} Ah | CC {rows[-1]['cc_charge_Ah']:.2f} Ah in {rows[-1]['cc_h']:.2f} h | CV {rows[-1]['cv_charge_Ah']:.2f} Ah in {rows[-1]['cv_h']:.2f} h", flush=True)
    out[f"tau{tau}"] = rows
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CM-BAT-R12d-cc-cv.json"), "w"), indent=1)
print("done", flush=True)
