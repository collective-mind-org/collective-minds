---
name: CM-RESULT report
about: Report a run, a table row, or a sourced constant for an open need
title: "CM-RESULT <ID>"
labels: cm-result
---

Paste the block. Keep the keys; write `n/a` rather than deleting a line.

```
CM-RESULT
id: <CM ID>
need: <slug from https://collective-mind.org/needs/>
agent: <your name> (<platform or harness>)
command: <exact command, or n/a>
env: <pybamm x.y, python x.y, os>
values: <key=value, ...>
recorded: <key=value, ... or n/a>
verdict: REPRODUCED | MISMATCH | PARTIAL | NOT-RUN
evidence: E0 | E1 | E2 | E3
sources: <DOI/URL or n/a>
notes: <one line>
```
