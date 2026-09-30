"""CM-CANCER-Q01 test bench v2: score a dosing rule against maximum-tolerated dose (MTD) in a two-population tumour model.
Generic Lotka-Volterra competition (sensitive S, resistant R; the adaptive-therapy setting of Gatenby 2009 / Zhang 2017,
normalised units, NOT fitted to any patient): dS/dt = rS*S*(1-(S+a*R)/K) - d*D(t)*S,  dR/dt = rR*R*(1-(R+b*S)/K).
Resistance costs fitness (rR < rS) and resistant cells are suppressed by sensitive competitors (b). Drug D in [0, 1].
Progression = total burden exceeds 1.2x its starting value. TTP = time to progression, reported relative to MTD.

v2 (2026-09-30, errata's review): v1's 2.48x bar was a setpoint, not a result. Time to progression is maximised by
containment at the largest tolerable burden (Viossat & Noble 2021, doi:10.1038/s41559-021-01428-w), so any rule that
parks the tumour nearer the 1.2x line, or looks more often, scored higher (modulate at target 1.15: 4.36x; on/off every
0.1 d at 1.199: 5.94x) without contributing an idea. Two changes:
  1. Every rule decides only at visits, every VISIT = 7 days; the dose is held between visits. A rule sees the burden
     S+R; using S or R separately is an 'oracle' (unobservable in a patient) and is labelled so.
  2. The bar is the containment FRONTIER: weekly Gatenby-style modulation (doi:10.1158/0008-5472.CAN-08-3658) scanned
     over its target burden. An entry beats the bar only if its TTP exceeds the best containment TTP achievable at the
     same or lower time-averaged burden. Score = TTP / frontier(mean burden); > 1.00 is an idea, <= 1.00 is containment.
Seconds to run, pure Python, no dependencies.
Usage: python3 results/cm_cancer_q01_dosing.py [rule]   rules: see RULES, or 'all'"""
import sys

P = dict(rS=0.035, rR=0.027, K=1.0, a=1.0, b=1.0, d=0.07)   # per day; generic, chosen so MTD fails within ~1-2 years
S0, R0, DT, TMAX, VISIT = 0.74, 0.01, 0.1, 3650.0, 7.0

def mtd(t, S, R, N0, state): return 1.0
def adaptive50(t, S, R, N0, state):
    """Zhang-2017-style: treat until burden falls to 50 % of start, pause until it regrows to 100 %."""
    N = S + R
    if state.get("on", True) and N <= 0.5 * N0: state["on"] = False
    elif not state.get("on", True) and N >= N0: state["on"] = True
    return 1.0 if state.get("on", True) else 0.0
def modulate_to(target):
    """Gatenby et al. 2009: 'treatment is continuously modulated to achieve a fixed tumor population'. Each visit:
    dose += 2 x (burden/N0 - target), clipped to [0, 1]. target 1.0 was v1's bar."""
    def rule(t, S, R, N0, state):
        state["D"] = min(1.0, max(0.0, state.get("D", 1.0) + 2.0 * ((S + R) / N0 - target))); return state["D"]
    return rule
def setpoint_088(t, S, R, N0, state):
    """agentcue 2026-09-30: D = clamp(20 (N - 0.88), 0, 1), 0.88 absolute (= 1.173 N0). Pure containment near the line."""
    return min(1.0, max(0.0, 20.0 * (S + R - 0.88)))
def composition_gate_oracle(t, S, R, N0, state, lo=0.2, hi=0.5):
    """attempt 2026-09-29, ORACLE version (reads the resistant share r = R/(S+R) directly, the upper bound for any
    estimate of it): r below hi -> MTD pulse while burden >= N0, then holiday; r at or above hi -> no drug until r falls
    back below lo. Tests whether gating dose on composition adds anything beyond containment."""
    r = R / (S + R)
    if r >= hi: state["stop"] = True
    elif r < lo: state["stop"] = False
    return 0.0 if state.get("stop") else (1.0 if S + R >= N0 else 0.0)
RULES = {"mtd": mtd, "adaptive50": adaptive50, "modulate": modulate_to(1.0), "setpoint_088": setpoint_088,
         "composition_gate_oracle": composition_gate_oracle}
ORACLE = {"composition_gate_oracle"}

def simulate(rule, p=P, visit=VISIT):
    S, R, t, state, N0, dose, D, next_visit, area = S0, R0, 0.0, {}, S0 + R0, 0.0, 0.0, 0.0, 0.0
    while t < TMAX:
        if t >= next_visit - 1e-9: D = rule(t, S, R, N0, state); next_visit += visit
        dose += D * DT; area += (S + R) / N0 * DT
        dS = p["rS"] * S * (1 - (S + p["a"] * R) / p["K"]) - p["d"] * D * S
        dR = p["rR"] * R * (1 - (R + p["b"] * S) / p["K"])
        S, R, t = max(S + DT * dS, 0.0), max(R + DT * dR, 0.0), t + DT
        if S + R > 1.2 * N0: break
    return dict(ttp_days=round(min(t, TMAX), 1), cumulative_dose=round(dose, 1), mean_burden=round(area / t, 3), progressed=t < TMAX)

def frontier():
    """Best containment TTP at each mean burden: weekly modulation over targets 0.30 ... 1.18."""
    pts = sorted((r["mean_burden"], r["ttp_days"]) for r in (simulate(modulate_to(0.30 + 0.005 * i)) for i in range(177)))
    return [(b, max(tt for bb, tt in pts if bb <= b)) for b, _ in pts]
def bar_at(front, mean_burden):
    ok = [tt for b, tt in front if b <= mean_burden + 1e-9]
    return max(ok) if ok else None

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    base = simulate(mtd)["ttp_days"]; front = frontier()
    print(f"visits every {VISIT:g} d; MTD TTP {base} d; containment frontier: best {max(t for _, t in front) / base:.2f}x MTD at mean burden {max(front, key=lambda x: x[1])[0]:.3f} N0")
    for name, rule in RULES.items():
        if which in ("all", name):
            r = simulate(rule); bar = bar_at(front, r["mean_burden"])
            score = f"{r['ttp_days'] / bar:.2f}x frontier" if bar else "below frontier range"
            print(f"{name:24s} TTP {r['ttp_days']:7.1f} d ({r['ttp_days'] / base:.2f}x MTD)  mean burden {r['mean_burden']:.3f} N0  dose {r['cumulative_dose']:6.1f}  "
                  f"score {score}{'  [oracle: uses S/R]' if name in ORACLE else ''}")
