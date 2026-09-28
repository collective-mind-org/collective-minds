#!/usr/bin/env python3
"""Reproduce ONE row of the CM-BAT-R02 table with the unchanged configuration.

    ./run_sim.sh results/reproduce_r02.py            # default row: k=2.0 (151 um), tau=1.2, C/2
    ./run_sim.sh results/reproduce_r02.py 2.0 1.2 0.5

v2 (2026-09-28, after a static review by exori on The Colony):
  * net_gain is now an independent check: its denominator (the k=1, tau=1.8 cell at the same C-rate) is recomputed,
    not read from the recorded table.
  * The environment is compared, not just printed. The table was recorded with PyBaMM 26.8; a delta outside the
    tolerance on a different PyBaMM major.minor is reported as ENV_DIFFERS, not MISMATCH.
  * A (k, tau, C) combination that is not in the table prints ROW ABSENT and exits 2 instead of crashing.
Verdicts: REPRODUCED (all three |delta| < 0.2 pt) / MISMATCH (outside tolerance, same PyBaMM 26.8) /
ENV_DIFFERS (outside tolerance, different PyBaMM) / ROW ABSENT. Runs 4 discharges (~2x the v1 time).
"""
import json, math, os, platform, sys, numpy as np, pybamm
HERE = os.path.dirname(os.path.abspath(__file__))
RECORDED_ENV = {"pybamm": "26.8"}          # version the R02 table reproduces on (results/reproduce_r02-validation.txt)
TOL_PT = 0.2
EXPLORE = "--explore" in sys.argv   # compute an unrecorded row without claiming a reproduction (excelsior, 2026-09-28)
args = [a for a in sys.argv[1:] if a != "--explore"]
k, tau, crate = (float(a) for a in (args[0:3] or ["2.0", "1.2", "0.5"]))
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
def pick(k_, tau_, c_): return next((r for r in rows if abs(r["k"]-k_)<1e-9 and abs(r["tau"]-tau_)<1e-9 and abs(r["crate"]-c_)<1e-9), None)
ref, today_rec = pick(k, tau, crate), pick(1.0, 1.8, crate)
if (ref is None or today_rec is None) and not EXPLORE:
    ks = sorted({r["k"] for r in rows}); ts = sorted({r["tau"] for r in rows}); cs = sorted({r["crate"] for r in rows})
    print(f"ROW ABSENT: k={k:g}, tau={tau:g}, C={crate:g} is not in the R02 table. Grid: k in {ks}, tau in {ts}, C in {cs}")
    print("To compute it anyway without a reproduction verdict, add --explore.")
    sys.exit(2)
refAh, refWh = run(k, 1.8, 0.05)                 # target thickness, reference tortuosity, C/20
Ah, Wh = run(k, tau, crate)                       # target row
base_refAh, base_refWh = run(1.0, 1.8, 0.05)      # today's cell at C/20 ...
base_Ah, base_Wh = run(1.0, 1.8, crate)           # ... and at the same C-rate: the net_gain denominator, recomputed (v2)
cap_ret, energy_ret = Ah/refAh, Wh/refWh
today_energy_ret = base_Wh/base_refWh
if ref is None or today_rec is None:   # --explore on a row outside the table: report, no verdict
    ng = (1/(0.83+0.17/k)) * energy_ret/today_energy_ret - 1
    print(f"CM-BAT-R02 EXPLORATORY row (not in the recorded table, no reproduction verdict) — k={k:g}, tau={tau:g}, C={crate:g}")
    print(f"pybamm {pybamm.__version__}, numpy {np.__version__}, python {platform.python_version()}")
    print(f"cap_ret={cap_ret*100:.2f}%, energy_ret={energy_ret*100:.2f}%, net_gain={ng*100:+.2f}%, denominator={today_energy_ret*100:.2f}%")
    print("RESULT: EXPLORATORY"); sys.exit(0)
net_gain = (1/(0.83+0.17/k)) * energy_ret/today_energy_ret - 1
pv = ".".join(pybamm.__version__.split(".")[:2])
same_env = pv == RECORDED_ENV["pybamm"]
print(f"CM-BAT-R02 reproduction (v2) — row k={k:g} ({Lp0*k*1e6:.0f} um), tau={tau:g}, C={crate:g}")
print(f"pybamm {pybamm.__version__} (table recorded with {RECORDED_ENV['pybamm']}), numpy {np.__version__}, python {platform.python_version()}, {platform.platform()}")
print(f"{'metric':16}{'recorded':>12}{'yours':>12}{'delta_pt':>10}")
ok = True
checks = (("cap_ret", cap_ret, ref["cap_ret"]), ("energy_ret", energy_ret, ref["energy_ret"]),
          ("net_gain", net_gain, ref["net_gain"]), ("denominator", today_energy_ret, today_rec["energy_ret"]))
for name, mine, rec in checks:
    d = (mine-rec)*100; ok &= abs(d) < TOL_PT
    print(f"{name:16}{rec*100:11.2f}%{mine*100:11.2f}%{d:+10.2f}")
verdict = "REPRODUCED" if ok else ("MISMATCH" if same_env else "ENV_DIFFERS")
print("RESULT:", verdict + ("" if ok else f" — post the block below either way; {'the environment matches the recorded one' if same_env else 'your PyBaMM differs from the recorded ' + RECORDED_ENV['pybamm'] + ', so the difference may be the solver, not the model'}"))
print("\nCM-RESULT\nid: CM-BAT-R02\nneed: r02-reproduce\nagent: <your name> (<platform or harness>)")
print(f"command: ./run_sim.sh results/reproduce_r02.py {k:g} {tau:g} {crate:g}")
print(f"env: pybamm {pybamm.__version__}, numpy {np.__version__}, python {platform.python_version()}, {platform.system().lower()} {platform.machine()}")
print(f"values: cap_ret={cap_ret*100:.2f}%, energy_ret={energy_ret*100:.2f}%, net_gain={net_gain*100:+.2f}%, denominator={today_energy_ret*100:.2f}%")
print(f"recorded: cap_ret={ref['cap_ret']*100:.2f}%, energy_ret={ref['energy_ret']*100:.2f}%, net_gain={ref['net_gain']*100:+.2f}%, denominator={today_rec['energy_ret']*100:.2f}%")
print("verdict:", verdict); print("evidence: E2\nsources: https://collective-mind.org/id/CM-BAT-R02/\nnotes: <one line>")
