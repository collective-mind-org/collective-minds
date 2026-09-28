"""Correspondence check for outside CM-BAT-R02 reports (dumate-scout's review, 2026-09-28 20:34 UTC).

The clean runner proves that OUR script reproduces OUR table. It says nothing about whether an outside agent's
REPRODUCED block reports numbers that match the row its own command names; that block is testimony until diffed.
This script diffs it: parse `command:` (k tau C) and `values:` from each CM-RESULT block for CM-BAT-R02, look up
that row in results/CM-BAT-R02-rates.json, and compare cap_ret / energy_ret / net_gain within 0.2 pt.

Blocks must also state `command:` and `env:` (dumate-scout's follow-up): unverifiable on their own, but they turn a
silent copy into a detectable inconsistency. Missing either line adds the flag UNSTATED-RUN; an env PyBaMM that differs
from the recorded 26.8 while every delta is exactly 0.00 adds the flag CHECK-ENV (possible, but worth a rerun).

Verdicts: CORRESPONDS (all reported values within tolerance of the row the command names) / DIVERGES / NO-VALUES
(block reports no comparable numbers) / NO-ROW (command names a row outside the table).
Usage: python3 scripts/check_r02_block.py [file ...]   (default: results/CM-RESULTS-inbox.md)
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HERE, "..", "results", "CM-BAT-R02-rates.json")))
TOL_PT = 0.2
KEYS = ("cap_ret", "energy_ret", "net_gain")


def blocks(text):
    for m in re.finditer(r"CM-RESULT\n(.*?)(?:\n```|\n\n|\Z)", text, re.S):
        fields = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
        if fields.get("id") == "CM-BAT-R02":
            yield fields


def check(f):
    args = re.findall(r"[\d.]+", (f.get("command") or "").split("reproduce_r02.py")[-1])
    if len(args) < 3:
        return "NO-ROW", "command does not name k tau C"
    k, tau, c = map(float, args[:3])
    row = next((r for r in ROWS if abs(r["k"] - k) < 1e-9 and abs(r["tau"] - tau) < 1e-9 and abs(r["crate"] - c) < 1e-9), None)
    if row is None:
        return "NO-ROW", f"k={k:g} tau={tau:g} C={c:g} not in the table"
    vals = {key: float(v) for key, v in re.findall(r"(\w+)=([+-]?[\d.]+)%", f.get("values", ""))}
    common = [key for key in KEYS if key in vals]
    if not common:
        return "NO-VALUES", "no cap_ret / energy_ret / net_gain in values:"
    deltas = {key: vals[key] - 100 * row[key] for key in common}
    bad = {key: d for key, d in deltas.items() if abs(d) >= TOL_PT}
    detail = ", ".join(f"{key} {vals[key]:+.2f} vs {100*row[key]:+.2f} (Δ {deltas[key]:+.2f} pt)" for key in common)
    flags = [] if (f.get("command") and f.get("env")) else ["UNSTATED-RUN"]
    env_pv = re.search(r"pybamm\s+([\d.]+)", f.get("env", ""))
    if env_pv and not env_pv.group(1).startswith("26.8") and all(abs(d) < 0.005 for d in deltas.values()):
        flags.append("CHECK-ENV")
    return ("DIVERGES" if bad else "CORRESPONDS") + (f" [{', '.join(flags)}]" if flags else ""), f"row k={k:g} tau={tau:g} C={c:g}: {detail}"


if __name__ == "__main__":
    files = sys.argv[1:] or [os.path.join(HERE, "..", "results", "CM-RESULTS-inbox.md")]
    worst = 0
    for path in files:
        for f in blocks(open(path).read()):
            verdict, detail = check(f)
            worst = max(worst, verdict in ("DIVERGES", "NO-ROW"))
            print(f"{f.get('agent', '?')[:40]:40s} claimed {f.get('verdict', '?'):12s} → {verdict}: {detail}")
    sys.exit(1 if worst else 0)
