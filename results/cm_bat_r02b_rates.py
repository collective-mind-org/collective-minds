import math, json, sys, numpy as np, pybamm
pybamm.set_logging_level("ERROR")
base = pybamm.ParameterValues("Chen2020")
Lp0, Ln0, Q0 = base["Positive electrode thickness [m]"], base["Negative electrode thickness [m]"], base["Nominal cell capacity [A.h]"]
eps_p, eps_n = base["Positive electrode porosity"], base["Negative electrode porosity"]
def b_for_tau(tau, eps): return 1 - math.log(tau)/math.log(eps)
def run(k, tau, crate):
    p = base.copy()
    p["Positive electrode thickness [m]"] = Lp0*k; p["Negative electrode thickness [m]"] = Ln0*k; p["Nominal cell capacity [A.h]"] = Q0*k
    for side, eps in (("Positive", eps_p), ("Negative", eps_n)):
        b = b_for_tau(tau, eps); p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
    sim = pybamm.Simulation(pybamm.lithium_ion.DFN(), parameter_values=p, experiment=pybamm.Experiment([f"Discharge at {crate}C until 2.5 V"]), solver=pybamm.IDAKLUSolver())
    sol = sim.solve()
    t = sol["Time [s]"].entries; V = sol["Voltage [V]"].entries; I = sol["Current [A]"].entries
    Wh = float(np.trapezoid(V*I, t)/3600); Ah = float(sol["Discharge capacity [A.h]"].entries[-1])
    return Ah, Wh
rows=[]
for k in [1.0, 1.5, 2.0, 3.0]:
    refAh, refWh = run(k, 1.8, 0.05)
    for crate in [0.33, 0.5, 1.0]:
        for tau in [1.2, 1.8, 3.0]:
            try: Ah, Wh = run(k, tau, crate)
            except Exception as e: Ah=Wh=float("nan"); print("fail",k,crate,tau,str(e)[:60],file=sys.stderr)
            rows.append({"k":k,"L_pos_um":Lp0*k*1e6,"crate":crate,"tau":tau,"Ah":Ah,"Wh":Wh,"refAh":refAh,"refWh":refWh,"cap_ret":Ah/refAh,"energy_ret":Wh/refWh})
            print(f"k={k:.1f} ({Lp0*k*1e6:.0f} um) C={crate:.2f} tau={tau:.1f}: cap {Ah/refAh*100:5.1f}%  energy {Wh/refWh*100:5.1f}%", flush=True)
base_e = next(r["energy_ret"] for r in rows if r["k"]==1.0 and r["tau"]==1.8 and r["crate"]==1.0)
print("\nNet cell Wh/kg vs today's cell (k=1, tau=1.8) at the SAME C-rate  [mass amortisation 1/(0.83+0.17/k) x energy retention ratio]:")
for crate in [0.33,0.5,1.0]:
    be = next(r["energy_ret"] for r in rows if r["k"]==1.0 and r["tau"]==1.8 and r["crate"]==crate)
    for r in rows:
        if r["crate"]!=crate: continue
        r["net_gain"] = (1/(0.83+0.17/r["k"])) * r["energy_ret"]/be - 1
        print(f"C={crate:.2f} k={r['k']:.1f} tau={r['tau']:.1f}: {r['net_gain']*100:+6.1f}%")
json.dump(rows, open("results/CM-BAT-R02-rates.json","w"), indent=1)
