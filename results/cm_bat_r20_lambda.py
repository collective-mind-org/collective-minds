"""CM-BAT-R20: test R16's usable-thickness map against a MEASURED plating rule.
Rule (Mijailovic et al., J. Electrochem. Soc. 2023, doi:10.1149/1945-7111/acd963, CM-LIT-0616, extracted by attempt,
verified verbatim): "For an 80% charge without lithium plating, a lambda < 0.6 is necessary", confirmed experimentally
"regardless of C-rate and thickness". Eq. 2 (transcribed by attempt): lambda = |i*| L / (K_eff * kappa_eff),
kappa_eff = kappa * eps_e / tau, K_eff = 0.08 V (paper's graphite).
Applied to R16's anode at C/2: i* = applied current density of the R16 cell (nominal capacity x k, O'Kane 2022 area),
L = anode thickness 85.2 um x k, eps_e = O'Kane anode porosity, tau = the row's tortuosity, kappa = Nyman2008 at 1 M, 25 C.
No simulation: an analytic map. Caveat: K_eff = 0.08 V was fitted for the paper's graphite, not O'Kane's."""
import json
import pybamm
p = pybamm.ParameterValues("OKane2022")
area = p["Electrode height [m]"] * p["Electrode width [m]"] * p["Number of electrodes connected in parallel to make a cell"]
Q = p["Nominal cell capacity [A.h]"]
L0 = p["Negative electrode thickness [m]"]; eps = p["Negative electrode porosity"]
k_fun = p["Electrolyte conductivity [S.m-1]"]
kappa = float(pybamm.Scalar(0).evaluate() + k_fun(pybamm.Scalar(1000.0), pybamm.Scalar(298.15)).evaluate()) if callable(k_fun) else float(k_fun)
K = 0.08
R16_USABLE = {1.2: 2.5, 1.8: 2.0, 3.0: 1.9}   # R16: last usable k at C/2 (cathode 189 / 151 / <151 um)
rows = []
for tau in (1.2, 1.5, 1.8, 2.4, 3.0):
    for k in (1.0, 1.5, 2.0, 2.5, 3.0):
        i = 0.5 * Q * k / area                   # A/m2 at C/2
        L = L0 * k
        lam = i * L / (K * kappa * eps / tau)
        rows.append({"tau": tau, "k": k, "anode_um": round(L * 1e6), "cathode_um": round(75.6 * k), "i_A_m2": round(i, 2),
                     "lambda": round(lam, 3), "measured_rule": "no plating to 80 % SOC" if lam < 0.6 else "plating before 80 % SOC",
                     "R16_usable": (k <= R16_USABLE.get(tau, 0)) if tau in R16_USABLE else None})
k_crit = {tau: round((0.6 * K * kappa * eps / tau / (0.5 * Q / area * L0)) ** 0.5, 2) for tau in (1.2, 1.5, 1.8, 2.4, 3.0)}
out = {"meta": {"kappa_S_m": round(kappa, 3), "eps_anode": eps, "area_m2": area, "Q_Ah": Q, "L0_um": L0 * 1e6, "K_eff_V": K},
       "k_at_lambda_0.6": k_crit, "rows": rows}
json.dump(out, open("results/cm_bat_r20_lambda.json", "w"), indent=1)
print(json.dumps(out["meta"])); print("k where lambda = 0.6:", k_crit)
for r in rows: print(r)
