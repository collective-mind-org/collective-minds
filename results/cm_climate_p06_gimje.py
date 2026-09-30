"""CM-CLIMATE-P06 R03: out-of-sample test of the Souza et al. 2021 CH4 model on a designed drainage trial.
Data: daily CH4 fluxes, Gimje, Korea, 2022-2024 (Zenodo doi:10.5281/zenodo.17111992, CC BY 4.0; Lee et al. 2024, Kim et al.
2023/2024, Rural Development Administration reports), triplicate plots: 'cf' (farmer practice, short drains at DAT ~31, 66,
89), mid-season drainage 14/21/28 days ('md_*'), and md + AWD from DAT ~95. Each file logs the water status per day.
Test: fit the model (r, kEh, kp, B0; no organic amendment term) to the MEAN of the cf plots of one year/field only, then
predict every other treatment of that year from its logged water schedule, and compare seasonal totals with measurement.
'awd' days are bracketed: all drained (upper bound on the model's AWD benefit) vs all flooded (lower bound).
Bmax: not in the data; set from grain yield x 2 (harvest index ~0.5; aria's assumption). Rice straw return: not recorded.
Usage: .venv/bin/python results/cm_climate_p06_gimje.py"""
import csv, glob, json, os
import numpy as np
from scipy.optimize import least_squares
import cm_climate_p06_souza as S

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "p06_gimje")
sys_meta = list(csv.reader(open(os.path.join(HERE, "p06_gimje", "meta.csv")))) if os.path.exists(os.path.join(D, "meta.csv")) else None

def plots():
    import subprocess
    rows = [r.split(",") for r in subprocess.run(["python3", os.path.join(HERE, "..", "scripts", "xlsx_dump.py"), os.path.join(D, "input_fields_meta.xlsx")],
                                                  capture_output=True, text=True).stdout.splitlines()[2:] if r and not r.startswith("###")]
    out = []
    for r in rows:
        if len(r) < 13 or not r[1].startswith("GJ"): continue
        f = os.path.join(D, "ch4", r[1] + ".csv")
        days = list(csv.DictReader(open(f)))
        out.append(dict(id=r[1], group=r[1][:10], wm=r[11], yield_g=float(r[10]), seasonal=float(r[12]),
                        status=[d["course_type"] for d in days], T=np.mean([float(d["tavg"]) for d in days]),
                        obs=[(float(d["DAT"]), float(d["ch4_flux"])) for d in days if d["ch4_flux"]]))
    return out

def simulate(x, status, T, Bmax, awd_drained, dt=0.1):
    r, kEh, kp, B0 = x
    n = len(status); t = np.arange(0.0, n, dt); B = Bmax / (1 + (Bmax / B0 - 1) * np.exp(-r * t))
    fT = 1.0 if T >= 30 else S.Q10 ** ((T - 30) / 10)
    Eh = np.empty_like(t); e = S.EH_AIR
    for i, ti in enumerate(t):
        st = status[min(int(ti), n - 1)]
        if st == "drainage" or (st == "awd" and awd_drained): e = S.EH_AIR
        else: e += -kEh * (e - S.EH_MIN) * dt
        Eh[i] = e
    fEh = np.where(Eh > S.EH_T, 0.0, (Eh - S.EH_T) / (S.EH_MIN - S.EH_T))
    return t, fT * fEh * (1 - B / Bmax) * kp * B

def season(t, E): return float(np.sum(E) * (t[1] - t[0]))   # mg m-2 -> x0.01 = kg/ha

if __name__ == "__main__":
    P = plots(); report = []
    for g in sorted({p["group"] for p in P}):
        grp = [p for p in P if p["group"] == g]; cf = [p for p in grp if p["wm"] == "cf"]
        if not cf: continue
        Bmax = 2 * np.mean([p["yield_g"] for p in grp]); T = cf[0]["T"]; status = cf[0]["status"]
        obs_d = sorted({d for p in cf for d, _ in p["obs"]}); obs_E = np.array([np.mean([v for p in cf for d, v in p["obs"] if d == dd]) * 1000 for dd in obs_d])  # g -> mg
        def resid(z):
            t, E = simulate(z, status, T, Bmax, True); return np.interp(obs_d, t, E) - obs_E
        fit = min((least_squares(resid, [0.08 * s, 0.2 * s, 0.5 * s, 20.0], bounds=([0.01, 0.005, 1e-4, 1.0], [0.5, 5.0, 50.0, 400.0])) for s in (0.5, 1, 2)), key=lambda res: res.cost)
        r2 = 1 - 2 * fit.cost / np.sum((obs_E - obs_E.mean()) ** 2)
        cf_model = season(*simulate(fit.x, status, T, Bmax, True)) / 100
        cf_meas = np.mean([p["seasonal"] for p in cf])
        print(f"\n{g}: cf fit R2 {r2:.2f}, cf seasonal model {cf_model:.1f} vs measured {cf_meas:.1f} kg/ha (mean of {len(cf)})")
        for wm in sorted({p["wm"] for p in grp} - {"cf"}):
            ps = [p for p in grp if p["wm"] == wm]; meas = [p["seasonal"] for p in ps]
            hi = season(*simulate(fit.x, ps[0]["status"], T, Bmax, True)) / 100; lo = season(*simulate(fit.x, ps[0]["status"], T, Bmax, False)) / 100
            m_cut = 1 - np.mean(meas) / cf_meas; p_cut = (1 - hi / cf_model, 1 - lo / cf_model)
            print(f"  {wm:16s} measured {np.mean(meas):5.1f} ± {np.std(meas):4.1f} kg/ha (cut {m_cut:+.0%})   model {min(hi,lo):5.1f}–{max(hi,lo):5.1f} (cut {min(p_cut):+.0%}…{max(p_cut):+.0%})")
            report.append(dict(group=g, wm=wm, measured=meas, measured_cut=round(m_cut, 3), model_cut=[round(v, 3) for v in sorted(p_cut)], cf_fit_R2=round(r2, 2)))
    json.dump(report, open(os.path.join(HERE, "CM-CLIMATE-P06-R03-gimje.json"), "w"), indent=1)
