"""CM-CANCER-Q01 test bench: score a dosing rule against maximum-tolerated dose (MTD) in a two-population tumour model.
Generic Lotka-Volterra competition (sensitive S, resistant R; the adaptive-therapy setting of Gatenby 2009 / Zhang 2017,
normalised units, NOT fitted to any patient): dS/dt = rS*S*(1-(S+a*R)/K) - d*D(t)*S,  dR/dt = rR*R*(1-(R+b*S)/K).
Resistance costs fitness (rR < rS) and resistant cells are suppressed by sensitive competitors (b). Drug D in [0, 1].
Progression = total burden exceeds 1.2x its starting value. Score = time to progression (TTP) relative to MTD. BAR: 'modulate' (Gatenby 2009 dose modulation), 2.48x.
Limitation: tumour burden has no cost here, so any rule that holds burden near its start value scores well; a new idea must beat 2.48x, not 1.49x.
Seconds to run, pure Python, no dependencies.
Usage: python3 results/cm_cancer_q01_dosing.py [rule]   rules: mtd, adaptive50, all   (add yours to RULES)"""
import sys

P = dict(rS=0.035, rR=0.027, K=1.0, a=1.0, b=1.0, d=0.07)   # per day; generic, chosen so MTD fails within ~1-2 years
S0, R0, DT, TMAX = 0.74, 0.01, 0.1, 3650.0

def mtd(t, S, R, N0, state): return 1.0
def adaptive50(t, S, R, N0, state):
    """Zhang-2017-style: treat until burden falls to 50 % of start, pause until it regrows to 100 %."""
    N = S + R
    if state.get("on", True) and N <= 0.5 * N0: state["on"] = False
    elif not state.get("on", True) and N >= N0: state["on"] = True
    return 1.0 if state.get("on", True) else 0.0
def modulate(t, S, R, N0, state):
    """Gatenby et al. 2009 (doi:10.1158/0008-5472.CAN-08-3658): 'treatment is continuously modulated to achieve a fixed
    tumor population'. Weekly: dose += 2 x (burden/N0 - 1), clipped to [0, 1]. Known best on this bench (bar since 2026-09-29)."""
    if "D" not in state: state.update(D=1.0, next=0.0)
    if t >= state["next"]: state["D"] = min(1.0, max(0.0, state["D"] + 2.0 * ((S + R) / N0 - 1.0))); state["next"] = t + 7.0
    return state["D"]
RULES = {"mtd": mtd, "adaptive50": adaptive50, "modulate": modulate}

def simulate(rule, p=P):
    S, R, t, state, N0, dose = S0, R0, 0.0, {}, S0 + R0, 0.0
    while t < TMAX:
        D = rule(t, S, R, N0, state); dose += D * DT
        dS = p["rS"] * S * (1 - (S + p["a"] * R) / p["K"]) - p["d"] * D * S
        dR = p["rR"] * R * (1 - (R + p["b"] * S) / p["K"])
        S, R, t = max(S + DT * dS, 0.0), max(R + DT * dR, 0.0), t + DT
        if S + R > 1.2 * N0: return dict(ttp_days=round(t, 1), cumulative_dose=round(dose, 1), progressed=True)
    return dict(ttp_days=TMAX, cumulative_dose=round(dose, 1), progressed=False)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    base = simulate(mtd)["ttp_days"]
    for name, rule in RULES.items():
        if which in ("all", name):
            r = simulate(rule); print(f"{name:12s} TTP {r['ttp_days']:7.1f} d  ({r['ttp_days'] / base:.2f}x MTD)  cumulative dose {r['cumulative_dose']}  progressed={r['progressed']}")
