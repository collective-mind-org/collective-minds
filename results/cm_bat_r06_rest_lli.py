"""CM-BAT-R06 (need 101a-rest-lli): lithium inventory lost to SEI during a 72 h rest at 70 C vs 25 C after 50 cycles at C/2.
Proxy for the Li-inventory cost of the thermal dendrite-healing dose of Li et al. Science 2018 (70 C, 3 days, no current).
Caveat stated up front: O'Kane 2022 is a graphite (LG M50) cell; SEI growth on Li metal is faster, so this is a LOWER bound.
Usage: ./run_sim.sh results/cm_bat_r06_rest_lli.py [N_cycles=50]"""
import json, sys, pybamm
pybamm.set_logging_level("ERROR")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
base = pybamm.ParameterValues("OKane2022")
print("SEI growth activation energy [J.mol-1] =", base["SEI growth activation energy [J.mol-1]"], "| pybamm", pybamm.__version__, flush=True)
model = pybamm.lithium_ion.DFN({"SEI": "solvent-diffusion limited", "SEI porosity change": "true",
                                "lithium plating": "partially reversible", "lithium plating porosity change": "true", "thermal": "lumped"})
cyc = [("Discharge at C/2 until 2.5 V", "Rest for 10 minutes", "Charge at C/2 until 4.2 V", "Hold at 4.2 V until C/20", "Rest for 10 minutes")] * N
VARS = ["Loss of lithium inventory [%]", "Loss of capacity to negative SEI [A.h]", "Loss of capacity to negative lithium plating [A.h]", "X-averaged negative SEI thickness [m]"]
out = {}
for T in (25, 70):
    rest = pybamm.step.string("Rest for 72 hours", temperature=f"{T}oC", period="10 minutes")
    exp = pybamm.Experiment(cyc + [rest])
    sim = pybamm.Simulation(model, parameter_values=base, experiment=exp, solver=pybamm.IDAKLUSolver())
    sol = sim.solve(save_at_cycles=[1, N, N + 1])
    end_cyc = sol.cycles[N - 1]; rest_sol = sol.cycles[N]
    b = {v: float(end_cyc[v].entries[-1]) for v in VARS}; a = {v: float(rest_sol[v].entries[-1]) for v in VARS}
    q0 = float(base["Nominal cell capacity [A.h]"])
    d_lli_pct = a[VARS[0]] - b[VARS[0]]; d_sei_ah = a[VARS[1]] - b[VARS[1]]; d_plat_ah = a[VARS[2]] - b[VARS[2]]
    out[f"rest_{T}C"] = {"T_C": T, "cycles": N, "before": b, "after": a, "delta_LLI_pct": d_lli_pct, "delta_LLI_Ah_est": d_lli_pct / 100 * q0,
                         "delta_SEI_Ah": d_sei_ah, "delta_plating_Ah": d_plat_ah, "delta_SEI_thickness_nm": (a[VARS[3]] - b[VARS[3]]) * 1e9}
    print(f"T={T} C: LLI {b[VARS[0]]:.3f}% -> {a[VARS[0]]:.3f}% (delta {d_lli_pct:+.3f} pt = {d_lli_pct/100*q0*1000:+.1f} mAh of {q0:.1f} Ah); "
          f"SEI loss {d_sei_ah*1000:+.1f} mAh, plating loss {d_plat_ah*1000:+.1f} mAh, SEI thickness {(a[VARS[3]]-b[VARS[3]])*1e9:+.1f} nm", flush=True)
    del sol, sim
json.dump(out, open("results/CM-BAT-R06-rest-lli.json", "w"), indent=1)
print("done", flush=True)
