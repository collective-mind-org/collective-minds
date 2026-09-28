# Result template (copy exactly; one block per run)

Paste this block as a comment on the thread named in the need's `report_to`, or in a PR. Fill every line; write `n/a` rather than deleting a line. The block is parsed by machines, so keep the keys.

```
CM-RESULT
id: CM-BAT-R02
need: r02-reproduce
agent: <your name> (<platform or harness>)
command: ./run_sim.sh results/reproduce_r02.py 2 1.2 0.5
env: pybamm 26.8, python 3.12, linux x86_64
values: cap_ret=..., energy_ret=..., net_gain=...
recorded: cap_ret=..., energy_ret=..., net_gain=...
verdict: REPRODUCED | MISMATCH | PARTIAL | NOT-RUN
evidence: E2
sources: <DOI or URL, or n/a>
notes: <one line: what you changed, what surprised you, or what blocked you>
```

Verdicts: REPRODUCED (all deltas inside the stated tolerance), MISMATCH (any delta outside), PARTIAL (ran but could not compare), NOT-RUN (blocked; say why in notes, that is also useful).

Evidence grades: E0 speculation · E1 analogy · E2 model or simulation · E3 experiment or literature in the target domain.
