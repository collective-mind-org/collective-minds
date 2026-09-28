# collective-minds

## Simulations
- Heavy simulations (PyBaMM etc.) run ONE at a time, always via `./run_sim.sh <script> [args]`. Never launch two in
  the background at once: two parallel DFN aging runs exhausted RAM and macOS started force-quitting the user's apps.
- Keep memory bounded inside scripts: `sim.solve(save_at_cycles=...)`, read end-of-life numbers from
  `sol.summary_variables`, never keep hundreds of full cycle solutions.
