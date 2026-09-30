#!/usr/bin/env python3
"""Replay test for the lit-quote rule (exori, 2026-09-30): 'text agreement and input agreement both stop short of
behaviour; known-bad rows in, expected verdicts out.' check_rule_copies.py proves the copies say the same thing; this
proves they do the same thing. Each fixture goes through BOTH validators, gateway/worker.js parse() (via node) and
scripts/lit_record.py check(), and must get the expected verdict from each. Fails on any disagreement.
Fixtures are the cases that actually got through, or nearly did, plus controls that must pass."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from lit_record import check

BASE = {"id": "CM-LIT-0999", "doi": "10.1000/replay", "agent": "replay (test)", "claim": "test claim"}
FIXTURES = [  # (name, fields, expected: "accept" | "reject")
    ("rosetta 2026-09-29: CM-LIT read filed as REPRODUCED, no quote", {"verdict": "REPRODUCED", "value": "4.3"}, "reject"),
    ("emi-ilands 2026-09-29: quote clipped at the decimal point", {"verdict": "EXTRACTED", "value": "3.5 mAh/cm2",
     "quote": "the areal capacity at onset reached 3."}, "reject"),
    ("CM-LIT-0617 #55: value not in quote", {"verdict": "EXTRACTED", "value": "ε=0.4",
     "quote": "the porosity of the graded electrode was varied across the thickness"}, "reject"),
    ("EXTRACTED, non-numeric value, no quote (the 2026-09-30 drift)", {"verdict": "EXTRACTED", "value": "increases"}, "reject"),
    ("PARTIAL with a number and a short quote", {"verdict": "PARTIAL", "value": "about 20 %", "quote": "20 %"}, "reject"),
    ("control: EXTRACTED, quote carries the number", {"verdict": "EXTRACTED", "value": "4.3",
     "quote": "the through-plane tortuosity was 4.3 for the calendered anode"}, "accept"),
    ("control: unicode minus normalised", {"verdict": "EXTRACTED", "value": "−20 °C",
     "quote": "cells were cycled at -20 °C for 100 cycles"}, "accept"),
    ("control: NO-ACCESS without a quote", {"verdict": "NO-ACCESS", "value": "NO-ACCESS"}, "accept"),
    ("control: OFF-TOPIC without a number", {"verdict": "OFF-TOPIC", "value": "not about batteries"}, "accept"),
    # KNOWN GAP (exori, 2026-09-30): a verbatim quote with a matching number, at a locator whose source was revised since and
    # no longer says it. Both validators accept it by design: text rules cannot see source versions. Expected 'accept' here so
    # the test documents the gap; the fix has to fetch the source (retrieval date + Crossref update-to / version check).
    ("KNOWN GAP: correct quote at a stale (since-revised) locator", {"verdict": "EXTRACTED", "value": "4.3",
     "quote": "the through-plane tortuosity was 4.3 for the calendered anode", "location": "v1 of a since-revised preprint"}, "accept"),
    # KNOWN GAP 2 (exori): verbatim text that exists, cited to the wrong document (preprint vs published, abstract vs paper).
    # Happened for real: CM-LIT-0520 (numbers from the full paper filed under a meeting-abstract DOI), caught only by a human
    # second reader (colonist-one, 2026-09-29). The DOI resolves, so the gateway accepts it.
    ("KNOWN GAP: right quote, wrong document (real case CM-LIT-0520)", {"verdict": "EXTRACTED", "value": "4.3", "doi": "10.1149/ma2025-023650mtgabs",
     "quote": "the through-plane tortuosity was 4.3 for the calendered anode"}, "accept"),
]

JS = r"""
const fs = require("fs"); const src = fs.readFileSync(process.argv[1], "utf8");
const grab = (re) => { const m = src.match(re); if (!m) throw new Error("not found: " + re); return m[0]; };
eval(grab(/const FIELDS = [^\n]*/).replace("const ", "var ") + "\n" + grab(/const VERDICTS = [^\n]*/).replace("const ", "var "));
var MAX = 1e6;
eval(src.slice(src.indexOf("function parse(block)"), src.indexOf("function r02row")));
const out = JSON.parse(fs.readFileSync(0, "utf8")).map(f =>
  parse(["CM-RESULT", ...Object.entries(f).map(([k, v]) => `${k}: ${v}`)].join("\n")).err ? "reject" : "accept");
console.log(JSON.stringify(out));
"""

def main():
    rows = [dict(BASE, **f) for _, f, _ in FIXTURES]
    gw = json.loads(subprocess.run(["node", "-e", JS, os.path.join(ROOT, "gateway/worker.js")], input=json.dumps(rows),
                                   capture_output=True, text=True, check=True).stdout)
    bad = 0
    for (name, _, want), row, g in zip(FIXTURES, rows, gw):
        p = "reject" if check(row) else "accept"
        ok = g == want and p == want; bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} expected {want:6s} gateway {g:6s} lit_record {p:6s}  {name}")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
