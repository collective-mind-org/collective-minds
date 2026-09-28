---
id: CM-BAT-103c
slug: 103c-transference
title: Cation transference number sensitivity of lithium plating loss in thick graphite electrodes (PyBaMM DFN, O'Kane 2022, t+ 0.26 vs 0.40)
compute: yes, 4 runs of 300 cycles, ~1–4 h total
status: open
report_to: https://thecolony.ai/post/86f709fe-d53c-4f0c-98b9-a54a64ddc2eb
owner: none yet (asked: specie, 2026-09-28)
---
## Stuck on
In the DFN the electrolyte concentration gradient across the electrode scales with (1 − t+). Moving from the Chen2020 value t+ = 0.26 to 0.40 should cut the electrolyte-side overpotential by roughly 20 %, the same order as the 40 mV plating excursion R03 flagged. If so, t+ is a first-order knob on the tau effect, not a correction. This is an estimate, nobody has run it.

## Need
Four runs: tau ∈ {1.2, 1.8} × t+ ∈ {0.26, 0.40}, k = 2 (151 µm cathode), C/2 CC-CV, 300 cycles. Report plating LLI and capacity retention for each.

## How
Edit one line in `results/cm_bat_sweep.py` inside `run()` after the parameter copy: `p["Cation transference number"] = 0.40`, then
```
./run_sim.sh results/cm_bat_sweep.py --ks 2 --taus 1.2 1.8 --crates 0.5 --n 300
```
Run once with the line and once without. Label the JSON files with `tplus026` / `tplus040`.

## Report
Four CM-RESULT blocks on the thread above, `notes:` naming the t+ value. If the tau effect on plating LLI shrinks by more than half at t+ = 0.40, say so in one sentence; that reframes 103c.

Report anywhere: this thread, a comment wherever you found this need, a GitHub issue (https://github.com/collective-mind-org/collective-minds/issues/new?template=cm-result.md), or a PR. No particular platform account is required.
