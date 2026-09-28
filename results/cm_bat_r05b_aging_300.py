"""CM-BAT-R05: cycle aging of a 151 um (2x) electrode at C/2 with SEI + Li plating submodels (O'Kane 2022), tau=1.2 vs 1.8.
Tests CM-BAT-103b (specie's reframing): does low tortuosity preserve cyclable capacity by keeping the anode out of the plating regime?
Runs in chunks of CH cycles, restarting from the last state, so memory stays bounded for any cycle count.
Usage: run_sim.sh results/cm_bat_r05b_aging_300.py <N_cycles> <tau> [chunk=30]"""
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
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
TAU = float(sys.argv[2])
CH = int(sys.argv[3]) if len(sys.argv) > 3 else 30
SAVE = set([1] + list(range(10, N+1, 10)) + [N])   # global cycle indices whose discharge capacity we record
CYCLE = ("Discharge at C/2 until 2.5 V", "Rest for 10 minutes", "Charge at C/2 until 4.2 V", "Hold at 4.2 V until C/20", "Rest for 10 minutes")
model = pybamm.lithium_ion.DFN({"SEI": "solvent-diffusion limited", "SEI porosity change": "true",
                                "lithium plating": "partially reversible", "lithium plating porosity change": "true"})
def disc_cap(cyc):
    st = cyc.steps[0]; return float(abs(st["Discharge capacity [A.h]"].entries[-1] - st["Discharge capacity [A.h]"].entries[0]))
out = {}
for k in [2.0]:
    for tau in [TAU]:
        try:
            pv = params(k, tau); caps = {}; done = 0; start = None; plated = sei = float("nan")
            while done < N:
                n = min(CH, N - done)
                sim = pybamm.Simulation(model, parameter_values=pv, experiment=pybamm.Experiment([CYCLE]*n), solver=pybamm.IDAKLUSolver())
                sol = sim.solve(starting_solution=start)
                cycles = sol.cycles[1:] if start is not None else sol.cycles   # cycle 0 is the wrapped starting state
                for j, cyc in enumerate(cycles, start=done+1):
                    if j in SAVE: caps[j] = disc_cap(cyc)
                sv = sol.summary_variables
                def last(name):
                    try: return float(sv[name][-1])
                    except Exception: return float("nan")
                plated = last("Loss of capacity to negative lithium plating [A.h]"); sei = last("Loss of capacity to negative SEI [A.h]")
                done += len(cycles)
                if len(cycles) < n:   # experiment terminated early (e.g. voltage cut-off): stop
                    print(f"  stopped early at cycle {done}", flush=True); break
                start = cycles[-1].steps[-1]   # carry only the final state forward
                print(f"  tau={tau}: {done}/{N} cycles, cap {caps.get(max(caps)):.3f} Ah, plating {plated:.3f} Ah", flush=True)
                del sim, sol, cycles
            ks = sorted(caps); caps_list = [caps[i] for i in ks]
            out[f"k{k}_tau{tau}"] = {"k": k, "tau": tau, "cycles_completed": done, "cap_first": caps_list[0], "cap_last": caps_list[-1],
                                     "retention": caps_list[-1]/caps_list[0], "LLI_plating_Ah": plated, "LLI_SEI_Ah": sei,
                                     "caps_at_cycles": dict(zip(map(str, ks), caps_list))}
            print(f"k={k} tau={tau}: {done} cycles, retention {caps_list[-1]/caps_list[0]*100:.1f}% ({caps_list[0]:.2f}->{caps_list[-1]:.2f} Ah), LLI plating {plated:.3f} Ah, SEI {sei:.3f} Ah", flush=True)
        except Exception as e:
            out[f"k{k}_tau{tau}"] = {"k": k, "tau": tau, "error": str(e)[:300]}; print(f"k={k} tau={tau}: FAILED {str(e)[:200]}", flush=True)
json.dump(out, open(f"results/CM-BAT-R05b-aging-300-tau{TAU}.json", "w"), indent=1)
