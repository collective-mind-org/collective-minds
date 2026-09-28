"""CM-BAT-R11 (excelsior's 'what the reproduction does not establish' list, item 1): mesh convergence of the R02 227 um row.
Re-runs reproduce_r02's exact run() for k=3, tau=1.2, C=0.33 with every mesh count doubled (var_pts x2) and compares
cap_ret / energy_ret / net_gain against the recorded table and against the default-mesh result. Pass: |delta| < 0.2 pt.
Usage: ./run_sim.sh results/cm_bat_r11_mesh.py [k=3] [tau=1.2] [C=0.33]"""
import json, math, os, sys, numpy as np, pybamm
HERE = os.path.dirname(os.path.abspath(__file__))
k, tau, crate = (float(a) for a in (sys.argv[1:4] or ["3.0", "1.2", "0.33"]))
pybamm.set_logging_level("ERROR")
base = pybamm.ParameterValues("Chen2020")
Lp0, Ln0, Q0 = base["Positive electrode thickness [m]"], base["Negative electrode thickness [m]"], base["Nominal cell capacity [A.h]"]
eps_p, eps_n = base["Positive electrode porosity"], base["Negative electrode porosity"]
def b_for_tau(tau, eps): return 1 - math.log(tau)/math.log(eps)
def run(k, tau, crate, mult):
    p = base.copy()
    p["Positive electrode thickness [m]"] = Lp0*k; p["Negative electrode thickness [m]"] = Ln0*k; p["Nominal cell capacity [A.h]"] = Q0*k
    for side, eps in (("Positive", eps_p), ("Negative", eps_n)):
        b = b_for_tau(tau, eps); p[f"{side} electrode Bruggeman coefficient (electrolyte)"] = b; p[f"{side} electrode Bruggeman coefficient (electrode)"] = b
    model = pybamm.lithium_ion.DFN(); vp = {key: int(v*mult) for key, v in model.default_var_pts.items()}
    sim = pybamm.Simulation(model, parameter_values=p, experiment=pybamm.Experiment([f"Discharge at {crate}C until 2.5 V"]), solver=pybamm.IDAKLUSolver(), var_pts=vp)
    sol = sim.solve(); t = sol["Time [s]"].entries; V = sol["Voltage [V]"].entries; I = sol["Current [A]"].entries
    return float(sol["Discharge capacity [A.h]"].entries[-1]), float(np.trapezoid(V*I, t)/3600), vp
rows = json.load(open(os.path.join(HERE, "CM-BAT-R02-rates.json")))["rows"] if "rows" in json.load(open(os.path.join(HERE, "CM-BAT-R02-rates.json"))) else json.load(open(os.path.join(HERE, "CM-BAT-R02-rates.json")))
def pick(k_, tau_, c_): return next(r for r in rows if abs(r["k"]-k_)<1e-9 and abs(r["tau"]-tau_)<1e-9 and abs(r["crate"]-c_)<1e-9)
ref = pick(k, tau, crate); today = pick(1.0, 1.8, crate)
out = {"row": {"k": k, "tau": tau, "crate": crate}, "recorded": {m: ref[m] for m in ("cap_ret", "energy_ret", "net_gain")}, "mesh": {}}
MULTS = [int(m) for m in os.environ.get("CM_MESH_MULTS", "1,2").split(",")]
for mult in MULTS:
    refAh, refWh, _ = run(k, 1.8, 0.05, mult); Ah, Wh, vp = run(k, tau, crate, mult)
    cap_ret, energy_ret = Ah/refAh, Wh/refWh; net_gain = (1/(0.83+0.17/k)) * energy_ret/today["energy_ret"] - 1
    out["mesh"][f"x{mult}"] = {"var_pts": vp, "cap_ret": cap_ret, "energy_ret": energy_ret, "net_gain": net_gain}
    print(f"mesh x{mult} {vp}: cap_ret {cap_ret*100:.3f}% energy_ret {energy_ret*100:.3f}% net_gain {net_gain*100:.3f}%  | delta vs recorded: {(cap_ret-ref['cap_ret'])*100:+.3f} {(energy_ret-ref['energy_ret'])*100:+.3f} {(net_gain-ref['net_gain'])*100:+.3f} pt", flush=True)
a, b = out["mesh"][f"x{MULTS[0]}"], out["mesh"][f"x{MULTS[-1]}"]
d = {m: (b[m]-a[m])*100 for m in ("cap_ret", "energy_ret", "net_gain")}; out["delta_x2_minus_x1_pt"] = d
print(f"mesh x{MULTS[-1]} - x{MULTS[0]} (pt):", {m: round(v, 4) for m, v in d.items()}, "| CONVERGED" if all(abs(v) < 0.2 for v in d.values()) else "| NOT CONVERGED", flush=True)
json.dump(out, open(os.path.join(HERE, f"CM-BAT-R11-mesh-k{k:g}-tau{tau:g}-C{crate:g}-m{'-'.join(map(str,MULTS))}.json"), "w"), indent=1)
