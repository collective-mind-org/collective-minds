"""CM-CLIMATE-P06 step 0: reproduce Souza, Yin & Calabrese 2021 (Geoderma 394:114986, doi:10.1016/j.geoderma.2021.114986),
'Optimal drainage timing for mitigating methane emissions from rice paddy fields', from its open data
(Texas Data Repository doi:10.18738/T8/TGY7TC, CC0; copied to results/p06_souza2021/) and the model in its accepted manuscript.

Model (Eqs. 1-9 of the paper):
  E = fT * fEh * fB * (kp*B + kC*B*C0*exp(-kd*t))            CH4, mg m-2 d-1
  fT = Q10**((T-30)/10) for T < 30 C, else 1; Q10 = 3
  fEh = 0 if Eh > Eh_t, else (Eh - Eh_t)/(Eh_min - Eh_t)
  fB = 1 - B/Bmax;   B = Bmax / (1 + kB*exp(-r*t)), kB = Bmax/B0 - 1
  dEh/dt = -kEh*(Eh - Eh_min) while flooded; during a drainage Eh jumps to aerated levels
Fitted per experiment (as in the paper): r, kEh, kp, B0, plus kd, kC when organically amended. Bmax, C0, T from the data.
ASSUMPTIONS not stated in the paper (aria): Eh_min = -200 mV (paper: 'around -200'), Eh_t = -100 mV (paper: methanogenesis
needs 'at least Eh < -100 mV'), Eh at flooding and after a drainage = +300 mV. kEh absorbs most of this choice.
Drainage in the data: td = day drained (200 = never), ldr = days drained (0 read as reflooded at once, Eh reset only).
Then, as in the paper: drain for 5 days at every td, eta(td) = (E_CF - E_D(td)) / E_CF, report eta_max and optimal td.
Usage: .venv/bin/python results/cm_climate_p06_souza.py"""
import glob, json, os
import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "p06_souza2021")
EH_MIN, EH_T, EH_AIR, Q10, DT = -200.0, -100.0, 300.0, 3.0, 0.1

def load(path):
    L = [l for l in open(path).read().splitlines() if l.strip()]; h = L[0].split(","); first = dict(zip(h, L[1].split(",")))
    pts = sorted((float(l.split(",")[0]), float(l.split(",")[1])) for l in L[1:])
    return dict(name=os.path.basename(path)[7:-4], t=np.array([p[0] for p in pts]), E=np.array([p[1] for p in pts]),
                C0=float(first["C0"]), T=float(first["Tavg"]), Bmax=float(first["Bmax"]), td=float(first["td"]), ldr=float(first["ldr"]))

def simulate(p, x, T_end, drains):
    """Daily-resolved emission on a DT grid. p: data dict; x: (r, kEh, kp, B0, kd, kC); drains: [(td, length)]."""
    r, kEh, kp, B0, kd, kC = x
    t = np.arange(0.0, T_end + DT, DT); B = p["Bmax"] / (1 + (p["Bmax"] / B0 - 1) * np.exp(-r * t))
    fT = 1.0 if p["T"] >= 30 else Q10 ** ((p["T"] - 30) / 10)
    Eh = np.empty_like(t); e = EH_AIR
    for i, ti in enumerate(t):
        if any(td <= ti < td + max(ln, DT) for td, ln in drains): e = EH_AIR
        else: e += -kEh * (e - EH_MIN) * DT
        Eh[i] = e
    fEh = np.where(Eh > EH_T, 0.0, (Eh - EH_T) / (EH_MIN - EH_T))
    E = fT * fEh * (1 - B / p["Bmax"]) * (kp * B + kC * B * p["C0"] * np.exp(-kd * t))
    return t, E

def total(t, E): return float(np.sum(E) * DT) / 1000.0   # g m-2

def fit(p):
    om = p["C0"] > 0; drains = [(p["td"], p["ldr"])] if p["td"] < 200 else []
    T_end = p["t"][-1]
    def unpack(z): return (z[0], z[1], z[2], z[3], z[4] if om else 0.0, z[5] if om else 0.0)
    def resid(z):
        t, E = simulate(p, unpack(z), T_end, drains)
        return np.interp(p["t"], t, E) - p["E"]
    z0 = [0.08, 0.2, 0.5, 20.0] + ([0.05, 0.1] if om else []); lo = [0.01, 0.005, 1e-4, 1.0] + ([0.001, 1e-5] if om else []); hi = [0.5, 5.0, 50.0, 400.0] + ([1.0, 50.0] if om else [])
    best = None
    for s in (0.5, 1.0, 2.0):   # a few starts; the paper used Levenberg-Marquardt (lmfit)
        res = least_squares(resid, [min(max(v * s, l * 1.01), h * 0.99) for v, l, h in zip(z0, lo, hi)], bounds=(lo, hi))
        if best is None or res.cost < best.cost: best = res
    x = unpack(best.x); pred = np.interp(p["t"], *simulate(p, x, T_end, drains)); ss = np.sum((p["E"] - p["E"].mean()) ** 2)
    return x, 1 - 2 * best.cost / ss, float(np.sqrt(2 * best.cost / len(p["E"])))

def eta_scan(p, x, T_end=None, length=5.0):
    T_end = T_end or max(p["t"][-1], 100.0)
    cf = total(*simulate(p, x, T_end, []))
    tds = np.arange(1.0, T_end - length, 1.0)
    eta = np.array([(cf - total(*simulate(p, x, T_end, [(td, length)]))) / cf for td in tds])
    return cf, tds, eta

if __name__ == "__main__":
    rows = []
    for path in sorted(glob.glob(os.path.join(DATA, "Data_*.csv"))):
        p = load(path); x, r2, rmse = fit(p); cf, tds, eta = eta_scan(p, x); i = int(np.argmax(eta))
        rows.append(dict(name=p["name"], amended=p["C0"] > 0, drained_at=None if p["td"] >= 200 else p["td"], R2=round(r2, 3), RMSE=round(rmse, 1),
                         params=dict(zip(["r", "kEh", "kp", "B0", "kd", "kC"], [round(float(v), 5) for v in x])),
                         E_CF_g_m2=round(cf, 1), eta_max=round(float(eta[i]), 3), td_opt=float(tds[i]),
                         eta_at_actual=None if p["td"] >= 200 else round(float(np.interp(p["td"], tds, eta)), 3)))
        r = rows[-1]; print(f"{r['name']:10s} {'OA' if r['amended'] else 'NA'} R2 {r['R2']:6.3f} RMSE {r['RMSE']:6.1f}  E_CF {r['E_CF_g_m2']:5.1f} g/m2  eta_max {r['eta_max']:.2f} at day {r['td_opt']:3.0f}"
                            + (f"  (drained day {r['drained_at']:.0f}: eta {r['eta_at_actual']:.2f})" if r["drained_at"] else ""), flush=True)
    for grp, flag in (("NA", False), ("OA", True)):
        g = [r for r in rows if r["amended"] == flag and not r["name"].startswith("Median")]
        print(f"{grp}: n={len(g)}  eta_max {np.mean([r['eta_max'] for r in g]):.2f} ± {np.std([r['eta_max'] for r in g]):.2f}  td_opt {np.mean([r['td_opt'] for r in g]):.0f} ± {np.std([r['td_opt'] for r in g]):.0f} d  (paper: NA ~0.35 at ~50 d, OA ~0.45 at ~18 d)")
    json.dump(rows, open(os.path.join(HERE, "CM-CLIMATE-P06-souza-repro.json"), "w"), indent=1)
