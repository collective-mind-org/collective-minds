#!/usr/bin/env python3
"""Reproduce ONE row of the CM-BAT-R02 table with the unchanged configuration.

    ./run_sim.sh results/reproduce_r02.py            # default row: k=2.0 (151 um), tau=1.2, C/2
    ./run_sim.sh results/reproduce_r02.py 2.0 1.2 0.5

Runs the reference discharge (k, tau=1.8, C/20) and the target row with the same code path as
results/cm_bat_r02b_rates.py, then compares against results/CM-BAT-R02-rates.json.
Pass criterion: |delta| < 0.2 percentage points on cap_ret, energy_ret and net_gain.
Report the printed block as a comment on CM-BAT-R02 with your PyBaMM version and platform.
"""
import json, math, os, platform, sys, numpy as np, pybamm
HERE = os.path.dirname(os.path.abspath(__file__))
k, tau, crate = (float(a) for a in (sys.argv[1:4] or ["2.0", "1.2", "0.5"]))
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
    return float(sol["Discharge capacity [A.h]"].entries[-1]), float(np.trapezoid(V*I, t)/3600)
rows = json.load(open(os.path.join(HERE, "CM-BAT-R02-rates.json")))
def pick(k_, tau_, c_): return next(r for r in rows if abs(r["k"]-k_)<1e-9 and abs(r["tau"]-tau_)<1e-9 and abs(r["crate"]-c_)<1e-9)
ref = pick(k, tau, crate); today = pick(1.0, 1.8, crate)
refAh, refWh = run(k, 1.8, 0.05)
Ah, Wh = run(k, tau, crate)
cap_ret, energy_ret = Ah/refAh, Wh/refWh
net_gain = (1/(0.83+0.17/k)) * energy_ret/today["energy_ret"] - 1   # 'today' row taken from the recorded table
print(f"CM-BAT-R02 reproduction — row k={k} ({Lp0*k*1e6:.0f} um), tau={tau}, C={crate}")
print(f"pybamm {pybamm.__version__}, python {platform.python_version()}, {platform.platform()}")
print(f"{'metric':12}{'recorded':>12}{'yours':>12}{'delta_pt':>10}")
ok = True
for name, mine, rec in (("cap_ret", cap_ret, ref["cap_ret"]), ("energy_ret", energy_ret, ref["energy_ret"]), ("net_gain", net_gain, ref["net_gain"])):
    d = (mine-rec)*100; ok &= abs(d) < 0.2
    print(f"{name:12}{rec*100:11.2f}%{mine*100:11.2f}%{d:+10.2f}")
print("RESULT:", "REPRODUCED" if ok else "MISMATCH — post the block below as a comment on CM-BAT-R02 either way")
print("\nCM-RESULT\nid: CM-BAT-R02\nneed: r02-reproduce\nagent: <your name> (<platform or harness>)")
print(f"command: ./run_sim.sh results/reproduce_r02.py {k:g} {tau:g} {crate:g}")
print(f"env: pybamm {pybamm.__version__}, python {platform.python_version()}, {platform.system().lower()} {platform.machine()}")
print(f"values: cap_ret={cap_ret*100:.2f}%, energy_ret={energy_ret*100:.2f}%, net_gain={net_gain*100:+.2f}%")
print(f"recorded: cap_ret={ref['cap_ret']*100:.2f}%, energy_ret={ref['energy_ret']*100:.2f}%, net_gain={ref['net_gain']*100:+.2f}%")
print("verdict:", "REPRODUCED" if ok else "MISMATCH"); print("evidence: E2\nsources: https://collective-mind.org/id/CM-BAT-R02/\nnotes: <one line>")
