"""CM-BAT-R09 (R07 protocol + SEI film resistance "distributed", holocene's question): does the 72 h 70 C healing dose hurt the cycles that follow?
50 cycles at C/2 -> 72 h rest at T -> 50 more cycles; compare retention and LLI in the second block for T = 25 vs 70 C.
Same model as R06 (OKane2022, SEI + partially reversible plating, lumped thermal). No SEI film resistance in this set,
so any penalty seen comes from inventory loss and porosity change, not ohmic SEI resistance (state that in the write-up).
Usage: ./run_sim.sh results/cm_bat_r09_post_dose_filmR.py [N=50]"""
import json, sys, pybamm
pybamm.set_logging_level("ERROR")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
base = pybamm.ParameterValues("OKane2022")
model = pybamm.lithium_ion.DFN({"SEI": "solvent-diffusion limited", "SEI porosity change": "true",
                                "lithium plating": "partially reversible", "lithium plating porosity change": "true", "thermal": "lumped", "SEI film resistance": "distributed"})
blk = [("Discharge at C/2 until 2.5 V", "Rest for 10 minutes", "Charge at C/2 until 4.2 V", "Hold at 4.2 V until C/20", "Rest for 10 minutes")]
out = {}
for T in (25, 70):
    rest = pybamm.step.string("Rest for 72 hours", temperature=f"{T}oC", period="10 minutes")
    back = pybamm.step.string("Rest for 2 hours", temperature="25oC", period="10 minutes")  # return to 25 C before cycling
    exp = pybamm.Experiment(blk * N + [rest, back] + blk * N)
    sim = pybamm.Simulation(model, parameter_values=base, experiment=exp, solver=pybamm.IDAKLUSolver())
    sol = sim.solve(save_at_cycles=[1, N, N + 3, 2 * N + 2])
    def cap(cyc): st = cyc.steps[0]; e = st["Discharge capacity [A.h]"].entries; return float(abs(e[-1] - e[0]))
    c1, cN, cN1, c2N = cap(sol.cycles[0]), cap(sol.cycles[N - 1]), cap(sol.cycles[N + 2]), cap(sol.cycles[2 * N + 1])
    lli = lambda cyc: float(cyc["Loss of lithium inventory [%]"].entries[-1])
    out[f"dose_{T}C"] = {"T_C": T, "N": N, "cap_cycle1": c1, "cap_cycleN": cN, "cap_first_after": cN1, "cap_last": c2N,
                         "retention_block1": cN / c1, "retention_block2": c2N / cN1, "retention_total": c2N / c1,
                         "lli_after_block1_pct": lli(sol.cycles[N - 1]), "lli_first_after_pct": lli(sol.cycles[N + 2]), "lli_end_pct": lli(sol.cycles[2 * N + 1])}
    o = out[f"dose_{T}C"]
    print(f"T={T} C: block1 {o['retention_block1']*100:.2f}% | first cycle after rest {cN1:.4f} Ah | block2 {o['retention_block2']*100:.2f}% | total {o['retention_total']*100:.2f}% | LLI {o['lli_after_block1_pct']:.3f} -> {o['lli_first_after_pct']:.3f} -> {o['lli_end_pct']:.3f} %", flush=True)
    del sol, sim
json.dump(out, open("results/CM-BAT-R09-post-dose-filmR.json", "w"), indent=1)
print("done", flush=True)
