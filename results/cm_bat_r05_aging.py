"""CM-BAT-R05: cycle aging of a 151 um (2x) electrode at C/2 with SEI + Li plating submodels (O'Kane 2022), tau=1.2 vs 1.8.
Tests CM-BAT-103b (specie's reframing): does low tortuosity preserve cyclable capacity by keeping the anode out of the plating regime?"""
import math, json, sys, pybamm
pybamm.set_logging_level("ERROR")
base = pybamm.ParameterValues("OKane2022")
Lp0, Ln0, Q0 = base["Positive electrode thickness [m]"], base["Negative electrode thickness [m]"], base["Nominal cell capacity [A.h]"]
eps_p, eps_n = base["Positive electrode porosity"], base["Negative electrode porosity"]
def b_for_tau(tau, eps): return 1 - math.log(tau)/math.log(eps)
def params(k, tau):
    p = base.copy()
    p["Positive electrode thickness [m]"] = Lp0*k; p["Negative electrode thickness [m]"] = Ln0*k; p["Nominal cell capacity [A.h]"] = Q0*k
    for side, eps in (("Positive", eps_p), ("Negative", eps_n)):
        b = b_for_tau(tau, eps); p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
    return p
N=int(sys.argv[1]) if len(sys.argv)>1 else 50
model = pybamm.lithium_ion.DFN({"SEI": "solvent-diffusion limited", "SEI porosity change": "true",
                                "lithium plating": "partially reversible", "lithium plating porosity change": "true"})
exp = pybamm.Experiment([("Discharge at C/2 until 2.5 V", "Rest for 10 minutes", "Charge at C/2 until 4.2 V", "Hold at 4.2 V until C/20", "Rest for 10 minutes")]*N)
out={}
for k in [1.0, 2.0]:
    for tau in [1.2, 1.8]:
        try:
            sim = pybamm.Simulation(model, parameter_values=params(k,tau), experiment=exp, solver=pybamm.IDAKLUSolver())
            sol = sim.solve()
            caps=[]; 
            for cyc in sol.cycles:
                st=cyc.steps[0]; caps.append(float(abs(st["Discharge capacity [A.h]"].entries[-1]-st["Discharge capacity [A.h]"].entries[0])))
            plated = float(sol["Loss of capacity to negative lithium plating [A.h]"].entries[-1]) if "Loss of capacity to negative lithium plating [A.h]" in sol.all_models[0].variables else float("nan")
            sei = float(sol["Loss of capacity to negative SEI [A.h]"].entries[-1]) if "Loss of capacity to negative SEI [A.h]" in sol.all_models[0].variables else float("nan")
            out[f"k{k}_tau{tau}"]={"k":k,"tau":tau,"cycles_completed":len(caps),"cap_first":caps[0],"cap_last":caps[-1],"retention":caps[-1]/caps[0],"LLI_plating_Ah":plated,"LLI_SEI_Ah":sei,"caps":caps}
            print(f"k={k} tau={tau}: {len(caps)} cycles, retention {caps[-1]/caps[0]*100:.1f}% ({caps[0]:.2f}->{caps[-1]:.2f} Ah), LLI plating {plated:.3f} Ah, SEI {sei:.3f} Ah", flush=True)
        except Exception as e:
            out[f"k{k}_tau{tau}"]={"k":k,"tau":tau,"error":str(e)[:300]}; print(f"k={k} tau={tau}: FAILED {str(e)[:200]}", flush=True)
json.dump(out, open("results/CM-BAT-R05-aging.json","w"), indent=1)
