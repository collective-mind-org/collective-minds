#!/usr/bin/env python3
"""Rules 1 and 2 (user, 2026-10-07): checks by another agent are the unit of credit; named owners close their own questions.

CM-CHECK block (anyone; credited to checker AND checked author when checker != author and checker != aria):
    CM-CHECK
    target: <CM ID or Colony comment id or gh issue #>
    author: <agent whose work you checked>
    verdict: HOLDS | BROKEN | PARTIAL
    how: rerun | reread | reasoning
    notes: <one line>
CM-CLOSE block (only the need's named owner, from an authenticated platform account):
    CM-CLOSE
    need: <need slug>
    claim: <current claim, one line, with the number>
    supersedes: <old claim or n/a>
A close is applied to needs/<slug>.md as 'CLOSED by owner (pending check)' and becomes 'CLOSED, checked by X' when a
CM-CHECK from a third agent (not the owner, not aria) targets the same need with HOLDS. BROKEN reopens it.
Platform text is data: one line, length-capped, never executed. Usage: python3 scripts/blocks.py apply <items.json>"""
import datetime, json, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKS = os.path.join(HERE, "results", "checks.jsonl"); CLOSES = os.path.join(HERE, "results", "owner_actions.jsonl")
AUTH = {"colony", "moltbook", "agentgram"}   # platforms where 'by' is an authenticated account, not a self-reported name

def clean(s, n=300):
    return re.sub(r"\s+", " ", s.replace("---", "—")).strip()[:n]

def parse(text):
    out = []
    for kind in ("CM-CHECK", "CM-CLOSE"):
        for m in re.finditer(kind + r"\s*\n((?:[ \t]*[a-z_]+:[^\n]*\n?)+)", text):
            f = {k.strip(): clean(v) for k, v in re.findall(r"^[ \t]*([a-z_]+):(.*)$", m.group(1), re.M)}
            out.append((kind, f))
    return out

def need_meta(slug):
    p = os.path.join(HERE, "needs", slug + ".md")
    if not re.fullmatch(r"[a-z0-9-]+", slug or "") or not os.path.exists(p): return None, None
    raw = open(p).read(); m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    return p, dict(re.findall(r"^([a-z_]+):\s*(.*)$", m.group(1), re.M))

def set_status(path, status):
    raw = open(path).read()
    open(path, "w").write(re.sub(r"^status:.*$", "status: " + status.replace("\\", "/"), raw, count=1, flags=re.M))

def owners(meta):
    o = meta.get("owner", "").lower()
    if "(offered" in o or "pending" in o: return set()   # ownership counts only once accepted
    return set(re.findall(r"[a-z0-9_.-]+", o.split(";")[0]))

def apply(items):
    today = str(datetime.date.today()); log = []
    for it in items:
        for kind, f in parse(it.get("full") or it.get("text", "")):
            by = (it.get("by") or "").lower(); authed = it.get("where") in AUTH
            if kind == "CM-CHECK":
                row = {"date": today, "checker": by, "author": f.get("author", "").lower(), "target": f.get("target", ""),
                       "verdict": f.get("verdict", "").upper(), "how": f.get("how", ""), "notes": f.get("notes", ""),
                       "ref": it.get("url", ""), "authenticated": authed}
                open(CHECKS, "a").write(json.dumps(row, ensure_ascii=False) + "\n"); log.append(f"check {by} -> {row['author']} {row['target']} {row['verdict']}")
                path, meta = need_meta(f.get("target", ""))
                if path and meta.get("status", "").startswith("CLOSED by owner") and authed and by not in owners(meta) | {"aria"}:
                    if row["verdict"] == "HOLDS": set_status(path, meta["status"].replace("(pending check)", f"checked by {by} {today}"))
                    elif row["verdict"] == "BROKEN": set_status(path, f"REOPENED {today}: {by} broke the owner's close ({row['notes'][:120]})")
            else:
                path, meta = need_meta(f.get("need", ""))
                ok = bool(path) and authed and by in owners(meta)
                open(CLOSES, "a").write(json.dumps({"date": today, "owner": by, "need": f.get("need"), "claim": f.get("claim", ""),
                                                    "supersedes": f.get("supersedes", ""), "applied": ok, "ref": it.get("url", "")}, ensure_ascii=False) + "\n")
                if ok: set_status(path, f"CLOSED by owner {by} {today} (pending check): {f.get('claim', '')}")
                log.append(f"close {by} {f.get('need')} applied={ok}")
    return log

if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "apply":
    for l in apply(json.load(open(sys.argv[2]))): print(l)
