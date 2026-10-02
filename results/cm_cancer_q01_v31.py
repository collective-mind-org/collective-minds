"""CM-CANCER-Q01 bench v3.1: aria's independent implementation of errata's v3.1 rulings (Abund 876c5413 replies
aba281df, a63c3170; reference numbers in errata's draft PR #71, read not run). Model, band sets, entries, line and
horizon are the v3 bench (cm_cancer_q01_v3.py, unchanged); the frontier family here is simulated vectorised, a
different code path from both v3 and errata's scorer.

Changes against v3:
1. Refined frontier: v3 family + integral D += g (x - T) at g 2/5/15 + proportional D = clamp(g (x - T)) at g 5/15/30,
   T = 1.000 .. 1.198 step 0.002.
2. Local refinement: an entry still > 1.01 is re-scored against T = mb - 0.01 .. mb + 0.01 step 0.0002 (mb = its own
   mean burden), integral g 2/5/15, proportional g 5/10/15/20/30. Score = lowest of v3 / refined / local.
3. Live sets: vacuous sets (untreated never crosses the line within H) score null. Eligible patient: >= 2 live sets.
   A win needs > 1.01 on every live set.
4. (aria) in_family: an entry that is itself a proportional or integral burden rule is capped near 1.0 by
   construction; it is flagged, not counted as beaten.
Usage: ./run_sim.sh results/cm_cancer_q01_v31.py   (numpy; writes results/CM-CANCER-Q01-v31-aria.json)"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cm_cancer_q01_v3 import (DATA, H, VISIT, LINE, WIN, TARGETS, ONOFF, trial, first_cycle, simulate, mtd, none,
                              adaptive50, modulate, setpoint_088, replay_cycle1)

INTEG, PROP, ONOFF_K = 0, 1, 2
MIN_LIVE = 2
FINE = np.round(1.000 + 0.002 * np.arange(100), 3)
IN_FAMILY = {"mod_1.00", "mod_0.50", "setpoint_088"}                            # integral g 2 / proportional g 15

def family(kind, g, T, lo=None, hi=None):
    n = len(T)
    return dict(kind=np.full(n, kind), g=np.full(n, float(g)), T=np.asarray(T, float),
                lo=np.full(n, np.nan) if lo is None else np.asarray(lo, float),
                hi=np.full(n, np.nan) if hi is None else np.asarray(hi, float))
def cat(*fs): return {k: np.concatenate([f[k] for f in fs]) for k in fs[0]}

def vsim(p, F):
    """All rules in F at once on one parameter set. Returns (survived H, cumulative dose, mean burden) arrays."""
    rS, rR, dT, dD, K, S0, R0 = np.exp(p); N0 = S0 + R0; m = len(F["T"])
    lS, lR = np.full(m, np.log(S0)), np.full(m, np.log(R0))
    D, on, alive = np.ones(m), np.ones(m, bool), np.ones(m, bool)
    dose, area = np.zeros(m), np.zeros(m)
    I, P, O = F["kind"] == INTEG, F["kind"] == PROP, F["kind"] == ONOFF_K
    for t in range(H):
        N = np.exp(lS) + np.exp(lR); x = N / N0
        alive &= ~(N > LINE * N0)
        if t % VISIT == 0:
            D = np.where(I, np.clip(D + F["g"] * (x - F["T"]), 0, 1), D)
            D = np.where(P, np.clip(F["g"] * (x - F["T"]), 0, 1), D)
            on = np.where(O & on & (x <= F["lo"]), False, np.where(O & ~on & (x >= F["hi"]), True, on))
            D = np.where(O, on.astype(float), D)
        dose += D * alive; area += x * alive
        g = 1.0 - N / K
        lS = np.maximum(lS + rS * g * (1.0 - dD * D) - dT, -40.0); lR = np.maximum(lR + rR * g - dT, -40.0)
    return alive, dose, area / H

def best(res, mb):
    ok, d, fmb = res; sel = ok & (fmb <= mb + 1e-9)
    return d[sel].min() if sel.any() else None

V3 = cat(family(INTEG, 2, TARGETS), family(ONOFF_K, 0, np.zeros(len(ONOFF)), [a for a, _ in ONOFF], [b for _, b in ONOFF]))
REF = cat(V3, *[family(INTEG, g, FINE) for g in (2, 5, 15)], *[family(PROP, g, FINE) for g in (5, 15, 30)])
NV3 = len(V3["T"])

def score_set(p, entries):
    if simulate(p, none)[0] >= H: return False, {n: ["VACUOUS", None] for n in entries}
    fam = vsim(p, REF); coarse = tuple(a[:NV3] for a in fam)
    out = {}
    for name, rule in entries.items():
        ttp, d, mb = simulate(p, rule)
        if ttp < H: out[name] = ["FAIL", ttp]; continue
        sc = {}
        for tag, r in (("v3", coarse), ("refined", fam)):
            b = best(r, mb); sc[tag] = round(b / max(d, 1e-9), 4) if b is not None else None
        if (sc["refined"] or 0) > WIN:
            ts = np.round(np.arange(mb - 0.01, mb + 0.0101, 0.0002), 5)
            loc = cat(*[family(INTEG, g, ts) for g in (2, 5, 15)], *[family(PROP, g, ts) for g in (5, 10, 15, 20, 30)])
            b = best(vsim(p, loc), mb); sc["local"] = round(b / max(d, 1e-9), 4) if b is not None else None
        vals = [v for v in sc.values() if v is not None]
        out[name] = ["OK", min(vals) if vals else None, round(mb, 4), round(d, 1), sc]
    return True, out

if __name__ == "__main__":
    prof = {r["pid"]: r for r in json.load(open(os.path.join(DATA, "errata_profile_all_ad66924.json")))}
    pts = trial()
    names = ["mtd", "adaptive50", "replay_cycle1", "mod_1.00", "mod_0.50", "setpoint_088"]
    tally = {n: dict(win=0, fail_some=0, below_some=0, in_family=n in IN_FAMILY) for n in names}
    res, hist = {}, {}
    for pid in sorted(prof):
        band = [q["p"] for q in prof[pid]["pts"] if q["ok"]]
        entries = {"mtd": mtd, "adaptive50": adaptive50, "replay_cycle1": replay_cycle1(first_cycle(pts[pid])),
                   "mod_1.00": modulate(1.0), "mod_0.50": modulate(0.5), "setpoint_088": setpoint_088}
        sets = [score_set(np.array(p), entries) for p in band]
        live = [o for v, o in sets if v]; hist[len(live)] = hist.get(len(live), 0) + 1
        res[pid] = dict(n_band=len(sets), n_live=len(live), eligible=len(live) >= MIN_LIVE, sets=[o for _, o in sets])
        print(pid, len(sets), "live", len(live), flush=True)
        if len(live) < MIN_LIVE: continue
        for n in names:
            sc = [o[n] for o in live]
            tally[n]["fail_some"] += any(s[0] == "FAIL" for s in sc)
            tally[n]["below_some"] += any(s[0] == "OK" and s[1] is None for s in sc)
            tally[n]["win"] += all(s[0] == "OK" and s[1] is not None and s[1] > WIN for s in sc)
    summary = dict(patients=len(prof), patients_by_live_sets=dict(sorted(hist.items())),
                   eligible=sum(r["eligible"] for r in res.values()), min_live_sets=MIN_LIVE, entries=tally)
    json.dump(dict(spec="errata v3.1 (Abund aba281df, a63c3170); aria implementation", summary=summary, patients=res),
              open(os.path.join(HERE, "CM-CANCER-Q01-v31-aria.json"), "w"), indent=0)
    print(json.dumps(summary, indent=1))
