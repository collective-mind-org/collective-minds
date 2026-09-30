"""CM-CLIMATE-P06 R04: does the CH4 / GWP benefit of AWD grow with the number of drying events or drying severity?
Data: Zhao et al. 2024 meta-analysis dataset (GCB, doi:10.1111/gcb.17581), Zenodo doi:10.5281/zenodo.14010496, CC BY 4.0,
262 AWD-vs-continuous-flooding comparisons. Effect = response ratio AWD/CF per comparison; summarised as the mean of
ln(RR) with a bootstrap 95 % CI (unweighted: most rows have n = 3 on both arms). Usage: python3 results/cm_climate_p06_zhao.py"""
import math, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts")); import xlsx_dump
rows = next(xlsx_dump.read(os.path.join(HERE, "p06_zhao2024", "AWD_on_greenhouse_gas241102.xlsx")))[1]
H = rows[0]; R = [dict(zip(H, r)) for r in rows[1:] if len(r) > 5]
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def lnrr(r, g):
    a, b = num(r.get(f"Mean_{g}_control")), num(r.get(f"Mean_{g}_AWD"))
    return math.log(b / a) if a and b and a > 0 and b > 0 else None
def summary(vals, B=2000, seed=1):
    random.seed(seed); m = sum(vals) / len(vals)
    bs = sorted(sum(random.choice(vals) for _ in vals) / len(vals) for _ in range(B))
    f = lambda v: f"{math.exp(v) - 1:+.0%}"
    return f"{f(m)} [{f(bs[int(.025 * B)])}, {f(bs[int(.975 * B)])}] n={len(vals)}"
def bins(r):
    n = num(r.get("Number of drying events")); return None if n is None else ("1" if n <= 1 else "2-3" if n <= 3 else "4-6" if n <= 6 else ">6")
if __name__ == "__main__":
    for g in ("CH4", "N2O", "GWP"):
        allv = [v for v in (lnrr(r, g) for r in R) if v is not None]; print(f"\n{g} all AWD: {summary(allv)}")
        for key, fn in (("threshold", lambda r: r.get("AWD threshold")), ("drying events", bins)):
            for level in sorted({fn(r) for r in R if fn(r)}, key=str):
                v = [x for x in (lnrr(r, g) for r in R if fn(r) == level) if x is not None]
                if len(v) >= 5: print(f"  {key:13s} {str(level):12s} {summary(v)}")
