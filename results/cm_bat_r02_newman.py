"""CM-BAT-R02: DFN (Newman) sweep — capacity retained at 1C vs electrode thickness and tortuosity.
Chen2020 (NMC811/graphite) parameters. Tortuosity set via Bruggeman b: tau = eps^(1-b)."""
import math, json, sys, pybamm
pybamm.set_logging_level("ERROR")
base = pybamm.ParameterValues("Chen2020")
Lp0, Ln0, Q0 = base["Positive electrode thickness [m]"], base["Negative electrode thickness [m]"], base["Nominal cell capacity [A.h]"]
eps_p, eps_n = base["Positive electrode porosity"], base["Negative electrode porosity"]
def b_for_tau(tau, eps): return 1 - math.log(tau)/math.log(eps)
def run(k, tau, crate):
    p = base.copy()
    p["Positive electrode thickness [m]"] = Lp0*k; p["Negative electrode thickness [m]"] = Ln0*k
    p["Nominal cell capacity [A.h]"] = Q0*k
    for side, eps in (("Positive", eps_p), ("Negative", eps_n)):
        b = b_for_tau(tau, eps)
        p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b
        p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
    model = pybamm.lithium_ion.DFN()
    exp = pybamm.Experiment([f"Discharge at {crate}C until 2.5 V"])
    sim = pybamm.Simulation(model, parameter_values=p, experiment=exp, solver=pybamm.IDAKLUSolver())
    sol = sim.solve()
    Ah = sol["Discharge capacity [A.h]"].entries[-1]; Wh = sol["Discharge energy [W.h]"].entries[-1] if "Discharge energy [W.h]" in sol.all_models[0].variables else float("nan")
    return Ah, Wh
rows=[]
for k in [1.0, 2.0, 3.0, 4.0]:
    ref_Ah, ref_Wh = run(k, 1.8, 0.05)
    for tau in [1.2, 1.8, 3.0]:
        try:
            Ah, Wh = run(k, tau, 1.0)
            ret = Ah/ref_Ah; eret = Wh/ref_Wh if ref_Wh==ref_Wh else float("nan")
        except Exception as e:
            Ah=Wh=ret=eret=float("nan"); print("fail",k,tau,str(e)[:80],file=sys.stderr)
        rows.append({"k":k,"L_pos_um":Lp0*k*1e6,"L_neg_um":Ln0*k*1e6,"tau":tau,"C20_Ah":ref_Ah,"Ah_1C":Ah,"cap_ret_1C":ret,"Wh_1C":Wh,"energy_ret_1C":eret})
        print(f"k={k:.0f} (pos {Lp0*k*1e6:.0f} um) tau={tau:.1f}: 1C {Ah:.2f} Ah / C20 {ref_Ah:.2f} Ah = {ret*100:.1f}% cap, energy {eret*100:.1f}%", flush=True)
json.dump(rows, open("results/CM-BAT-R02-newman.json","w"), indent=1)
# combine with R01b mass accounting: per-area inactive fraction 17% at k=1
print("\nEffective cell Wh/kg vs baseline (mass amortisation x energy retention at 1C):")
for r in rows:
    k=r["k"]; mass_gain = 1/(0.83 + 0.17/k)
    eff = mass_gain * r["energy_ret_1C"] / next(x["energy_ret_1C"] for x in rows if x["k"]==1.0 and x["tau"]==1.8)
    r["eff_cell_gain_vs_base_1C"]=eff
    print(f"k={k:.0f} tau={r['tau']:.1f}: mass x{mass_gain:.3f} * energy-ret {r['energy_ret_1C']*100:.1f}% -> {(eff-1)*100:+.1f}% vs today's cell at 1C")
json.dump(rows, open("results/CM-BAT-R02-newman.json","w"), indent=1)
