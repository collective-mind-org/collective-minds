"""CM-BAT-R21: first test of the lambda rule against a MEASURED plating onset on a >150 um graphite anode.
Measured (Ma et al., ACS AMI 2022, doi:10.1021/acsami.2c16090, CM-LIT-0617, 7 quoted extractions by attempt):
~380-385 um graphite, ~17 mg/cm2, porosity 0.4, operando optical + voltage; "At 2 mA cm-2, the critical Li plating
capacity was 4.2 mAh cm-2 at room temperature" -> onset SOC = 4.2 / (17 mg/cm2 x 340-372 mAh/g) = 66-73 %.
Prediction: lambda = i L / (K kappa eps/tau), K 0.08 V; map lambda -> onset SOC with our own full-cell collapse
(R20b: lambda 0.6 -> 69.6 %, lambda 1.0 -> 35.4 %; linear between, 'no onset before ~80 %' below lambda ~0.49).
The electrode's tortuosity was not reported, so it is scanned. Output: results/cm_bat_r21_ma2022.json"""
import json
i, L, eps, kappa, K = 20.0, 385e-6, 0.4, 0.95, 0.08
q_lo, q_hi = 17 * 0.340, 17 * 0.372
meas = (100 * 4.2 / q_hi, 100 * 4.2 / q_lo)
def onset(lam):   # R20b collapse, linear interpolation/extrapolation between the two measured-in-model points
    return 69.6 + (lam - 0.6) * (35.4 - 69.6) / 0.4
rows = []
for tau in (1.58, 2.0, 2.37, 3.0, 4.3, 5.5):
    lam = i * L / (K * kappa * eps / tau)
    rows.append({"tau": tau, "lambda": round(lam, 3), "predicted_onset_SOC_pct": round(onset(lam), 1) if lam >= 0.49 else ">~80 (no plating to 80 %)"})
tau_match = 0.6 * K * kappa * eps / (i * L)
out = {"measured_onset_SOC_pct": [round(meas[0], 1), round(meas[1], 1)], "tau_for_lambda_0.6": round(tau_match, 2), "rows": rows,
       "notes": "Bruggeman tau for eps 0.4 is 1.58; EIS through-plane tau for flake graphite ~4.3 at eps 0.54 (CM-LIT-0520); kappa for 1 M LiPF6 carbonate at RT ~0.95 S/m (EC/PC/EMC may differ)."}
json.dump(out, open("results/cm_bat_r21_ma2022.json", "w"), indent=1); print(json.dumps(out, indent=1))
