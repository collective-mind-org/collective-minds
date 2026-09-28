"""CM-BAT-103a: charge acceptance of thick electrodes vs tortuosity. CC charge at 1C/2C from 2.5 V to 4.2 V (no CV hold), capacity accepted / C/20 capacity."""
import math, json, sys, pybamm
pybamm.set_logging_level("ERROR")
base = pybamm.ParameterValues("Chen2020")
Lp0, Ln0, Q0 = base["Positive electrode thickness [m]"], base["Negative electrode thickness [m]"], base["Nominal cell capacity [A.h]"]
eps_p, eps_n = base["Positive electrode porosity"], base["Negative electrode porosity"]
def b_for_tau(tau, eps): return 1 - math.log(tau)/math.log(eps)
def params(k, tau):
    p = base.copy()
    p["Positive electrode thickness [m]"] = Lp0*k; p["Negative electrode thickness [m]"] = Ln0*k; p["Nominal cell capacity [A.h]"] = Q0*k
    for side, eps in (("Positive", eps_p), ("Negative", eps_n)):
        b = b_for_tau(tau, eps); p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
    return p
def run(k, tau, crate):
    p = params(k, tau)
    exp = pybamm.Experiment([("Discharge at C/20 until 2.5 V", "Rest for 30 minutes", f"Charge at {crate}C until 4.2 V")])
    sim = pybamm.Simulation(pybamm.lithium_ion.DFN(), parameter_values=p, experiment=exp, solver=pybamm.IDAKLUSolver())
    sol = sim.solve()
    step = sol.cycles[0].steps[2]
    Ah_in = abs(step["Discharge capacity [A.h]"].entries[-1] - step["Discharge capacity [A.h]"].entries[0])
    # min anode potential vs Li as plating proxy (if available)
    try: phi_min = float(min(step["Negative electrode surface potential difference [V]"].entries.min(axis=0)))
    except Exception: phi_min = float("nan")
    return Ah_in, phi_min
rows=[]
for k in [1.0, 1.5, 2.0]:
    refAh = run(k, 1.8, 0.05)[0]
    for crate in [0.5, 1.0, 2.0]:
        for tau in [1.2, 1.8, 3.0]:
            try: Ah, phi = run(k, tau, crate)
            except Exception as e: Ah=phi=float("nan"); print("fail",k,crate,tau,str(e)[:60],file=sys.stderr)
            rows.append({"k":k,"L_pos_um":Lp0*k*1e6,"crate":crate,"tau":tau,"Ah_accepted":Ah,"refAh":refAh,"acceptance":Ah/refAh,"min_anode_eta_V":phi})
            print(f"k={k:.1f} ({Lp0*k*1e6:.0f} um) charge {crate:.1f}C tau={tau:.1f}: accepted {Ah/refAh*100:5.1f}%  min anode overpotential {phi:+.3f} V", flush=True)
json.dump(rows, open("results/CM-BAT-R03-charge.json","w"), indent=1)
