"""Quote-in-source scope measurement (queue item quote-in-source; three-state design from arion, Colony 7291c914/806e6e0a).
For every gateway lit claim that carries a quote, fetch the free surfaces we can reach without keys (Crossref abstract,
OpenAlex abstract) and grade: IN (quote found, normalised) / NOT-IN-SCOPE (only abstract reachable, quote absent) /
NO-SURFACE (nothing fetchable). Records which surface was searched, so a later full-text pass can re-grade.
Usage: python3 scripts/quote_scope.py  -> results/quote_scope.json"""
import json, re, unicodedata, urllib.request, html, time
UA = {"User-Agent": "collective-mind/aria (mailto:aria@collective-mind.org)"}
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r: return json.load(r)
    except Exception: return None
def norm(s):
    s = unicodedata.normalize("NFKC", html.unescape(re.sub(r"<[^>]+>", " ", s or "")))
    s = s.translate(str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
                                   "‘": "'", "’": "'", "“": '"', "”": '"', " ": " "}))
    s = re.sub(r"-\s+", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()
def surfaces(doi):
    out = {}
    cr = get(f"https://api.crossref.org/works/{doi}")
    if cr and cr.get("message", {}).get("abstract"): out["crossref-abstract"] = cr["message"]["abstract"]
    oa = get(f"https://api.openalex.org/works/doi:{doi}")
    inv = (oa or {}).get("abstract_inverted_index")
    if inv:
        pos = sorted((i, w) for w, ii in inv.items() for i in ii); out["openalex-abstract"] = " ".join(w for _, w in pos)
    return out
import os
CACHE = "results/quote_scope_issues.json"  # issue bodies (GitHub allows 60 unauthenticated requests/h)
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def issue_body(n):
    if str(n) not in cache:
        b = (get(f"https://api.github.com/repos/collective-mind-org/collective-minds/issues/{n}") or {}).get("body")
        if b is None: raise SystemExit(f"GitHub fetch failed at issue {n} (rate limit?); rerun later")
        cache[str(n)] = b; json.dump(cache, open(CACHE, "w"))
    return cache[str(n)]
q = json.load(open("results/lit_queue.json"))["papers"]
rows = []
for p in q:
    for c in p.get("claims", []):
        iss = c.get("issue")
        if not iss: continue
        body = issue_body(iss) or ""
        m = re.search(r"^quote:\s*(.+)$", body, re.M)
        v = re.search(r"^verdict:\s*(\S+)", body, re.M)
        if not m: continue
        quote = m.group(1).strip().strip('"“”')
        srf = surfaces(p["doi"]); nq = norm(quote)
        squash = lambda x: re.sub(r"\s+", "", x)  # OpenAlex tokenises "kg–1" as "kg –1" (CM-LIT-0028 false negative)
        hit = [k for k, t in srf.items() if nq and squash(nq) in squash(norm(t))]
        state = "IN" if hit else ("NOT-IN-SCOPE" if srf else "NO-SURFACE")
        rows.append({"id": p["id"], "doi": p["doi"], "issue": iss, "agent": c.get("agent"), "verdict": v.group(1) if v else None,
                     "state": state, "searched": sorted(srf), "found_in": hit, "quote": quote[:300],
                     "fetched": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())})
        print(p["id"], iss, state, sorted(srf), flush=True)
json.dump(rows, open("results/quote_scope.json", "w"), indent=1)
from collections import Counter; print(Counter(r["state"] for r in rows), "of", len(rows))
