"""CM-CLIMATE-P06 R06: calibrate soil re-reduction after reflooding on a designed trial, then re-ask R02's question.
R02 found the Souza et al. 2021 model predicts 2-3 drains cut CH4 by 65-100 %, while measured AWD cuts ~50 %. Suspect: one
redox rate kEh for both the first flood and every reflood. Here the model gets a separate post-reflood rate kR (and, as a
second variant, a post-drain lag L before methanogenesis resumes). Data: Gimje trial (R03; Zenodo 10.5281/zenodo.17111992),
treatment means of triplicate plots. Fit per year on the non-AWD treatments jointly (cf + md 14/21/28 d share plant and soil
parameters r, kEh, kp, B0 and kR); AWD plots are held out and predicted with 'awd' days as drained / as flooded.
Usage: .venv/bin/python results/cm_climate_p06_recovery.py"""
import json, os
import numpy as np
from scipy.optimize import least_squares
import cm_climate_p06_souza as S
import cm_climate_p06_gimje as G

def simulate(x, status, T, Bmax, awd_drained, dt=0.2):
    r, kEh, kp, B0, kR = x
    n = len(status); t = np.arange(0.0, n, dt); B = Bmax / (1 + (Bmax / B0 - 1) * np.exp(-r * t))
    fT = 1.0 if T >= 30 else S.Q10 ** ((T - 30) / 10)
    Eh = np.empty_like(t); e = S.EH_AIR; reflooded = False
    for i, ti in enumerate(t):
        st = status[min(int(ti), n - 1)]
        if st == "drainage" or (st == "awd" and awd_drained): e = S.EH_AIR; reflooded = True
        else: e += -(kR if reflooded else kEh) * (e - S.EH_MIN) * dt
        Eh[i] = e
    fEh = np.where(Eh > S.EH_T, 0.0, (Eh - S.EH_T) / (S.EH_MIN - S.EH_T))
    return t, fT * fEh * (1 - B / Bmax) * kp * B

def season(t, E): return float(np.sum(E) * (t[1] - t[0]))

def treatment_means(grp):
    out = {}
    for wm in sorted({p["wm"] for p in grp}):
        ps = [p for p in grp if p["wm"] == wm]; days = sorted({d for p in ps for d, _ in p["obs"]})
        out[wm] = dict(status=ps[0]["status"], d=np.array(days), E=np.array([np.mean([v for p in ps for dd, v in p["obs"] if dd == d]) * 1000 for d in days]),
                       seasonal=float(np.mean([p["seasonal"] for p in ps])))
    return out

def fit(tm, T, Bmax, shared_kR):
    fitset = {k: v for k, v in tm.items() if "awd" not in k}
    def unpack(z): return (z[0], z[1], z[2], z[3], z[1] if shared_kR else z[4])
    def resid(z):
        x = unpack(z); return np.concatenate([np.interp(v["d"], *simulate(x, v["status"], T, Bmax, True)) - v["E"] for v in fitset.values()])
    lo = [0.01, 0.005, 1e-4, 1.0] + ([] if shared_kR else [0.001]); hi = [0.5, 5.0, 50.0, 400.0] + ([] if shared_kR else [5.0])
    best = min((least_squares(resid, [min(max(v, l * 1.01), h * .99) for v, l, h in zip([0.08 * s, 0.2 * s, 0.5 * s, 20.0] + ([] if shared_kR else [0.05 * s]), lo, hi)], bounds=(lo, hi))
                for s in (0.5, 1, 2)), key=lambda r_: r_.cost)
    allE = np.concatenate([v["E"] for v in fitset.values()])
    return unpack(best.x), 1 - 2 * best.cost / np.sum((allE - allE.mean()) ** 2)

if __name__ == "__main__":
    P = G.plots(); report = []
    for g in ("GJ20220101", "GJ20230101", "GJ20240101"):
        grp = [p for p in P if p["group"] == g]; tm = treatment_means(grp)
        Bmax = 2 * np.mean([p["yield_g"] for p in grp]); T = grp[0]["T"]
        for shared in (True, False):
            x, r2 = fit(tm, T, Bmax, shared)
            cf = season(*simulate(x, tm["cf"]["status"], T, Bmax, True))
            line = f"{g[2:6]} {'v1 kR=kEh' if shared else 'v2 kR free':10s} R2 {r2:.2f}  kEh {x[1]:.3f}  kR {x[4]:.3f}/d"
            rows = []
            for wm, v in tm.items():
                if wm == "cf": continue
                hi_ = 1 - season(*simulate(x, v["status"], T, Bmax, True)) / cf; lo_ = 1 - season(*simulate(x, v["status"], T, Bmax, False)) / cf
                meas = 1 - v["seasonal"] / tm["cf"]["seasonal"]
                rows.append(dict(wm=wm, measured_cut=round(meas, 3), model_cut=sorted([round(lo_, 3), round(hi_, 3)]), held_out="awd" in wm))
                line += f"\n     {wm:16s} measured {meas:+.0%}  model {min(lo_, hi_):+.0%}…{max(lo_, hi_):+.0%}{'  (held out)' if 'awd' in wm else ''}"
            print(line, flush=True)
            report.append(dict(group=g, variant="v1" if shared else "v2", R2=round(r2, 3), kEh=round(x[1], 4), kR=round(x[4], 4), rows=rows))
    json.dump(report, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "CM-CLIMATE-P06-R06-recovery.json"), "w"), indent=1)
