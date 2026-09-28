#!/usr/bin/env python3
"""Record one literature-audit submission (a gateway issue labelled cm-result) and close it.

Reads the CM-RESULT block from the GitHub issue, appends it to results/lit_claims.jsonl with the maintainer's
claim_check, moves the paper's status in results/lit_queue.json, comments and closes the issue.
Status rules: EXTRACTED on an open paper → extracted-1; a second EXTRACTED by a DIFFERENT agent → pass
--agrees or --disputes (a human/maintainer judgement, never automatic); NO-ACCESS leaves status unchanged;
OFF-TOPIC → off-topic.

Usage: python3 scripts/lit_record.py ISSUE "claim_check text" "comment text" [--agrees|--disputes] [--flag NAME]
"""
import json, re, subprocess, sys, time, urllib.request

REPO = "collective-mind-org/collective-minds"


def token():
    out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True).stdout
    return dict(l.split("=", 1) for l in out.strip().splitlines())["password"]


def gh(path, body=None, method=None):
    h = {"Authorization": "token " + token(), "Content-Type": "application/json"}
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}{path}", data=json.dumps(body).encode() if body else None,
                                 headers=h, method=method or ("POST" if body else "GET"))
    return json.load(urllib.request.urlopen(req))


def main():
    a = sys.argv[1:]
    issue, check, comment = int(a[0]), a[1], a[2]
    agrees, disputes = "--agrees" in a, "--disputes" in a
    flag = a[a.index("--flag") + 1] if "--flag" in a else None
    body = gh(f"/issues/{issue}")["body"]
    blk = body[body.find("CM-RESULT"):]
    blk = blk[:blk.find("```")] if "```" in blk else blk
    f = dict(re.findall(r"^(\w+):\s*(.*)$", blk, re.M))
    pid, agent, verdict = f["id"], f.get("agent", "?").split(" (")[0], f.get("verdict", "?")
    rec = {"paper": pid, "doi": f.get("doi"), "agent": agent, "issue": issue, "verdict": verdict, "claim": f.get("claim"), "quote": f.get("quote"),
           "value": f.get("value"), "conditions": f.get("conditions"), "location": f.get("location"), "doi_check": "resolves (Crossref, gateway)",
           "claim_check": check, "recorded": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}
    if flag: rec["flag"] = flag
    if (agrees or disputes) and len(f.get("quote") or "") < 20:
        sys.exit("refusing --agrees/--disputes: the report has no verbatim quote (re-derivation rule, needs/lit-audit.md)")
    open("results/lit_claims.jsonl", "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    q = json.load(open("results/lit_queue.json")); papers = q if isinstance(q, list) else q["papers"]
    p = next(x for x in papers if x["id"] == pid)
    prior = {c.get("agent") for c in p.get("claims", []) if c.get("value") not in (None, "NO-ACCESS")}
    p.setdefault("claims", []).append({"agent": agent, "issue": issue, "value": rec["value"] if verdict != "NO-ACCESS" else "NO-ACCESS", **({"flag": flag} if flag else {})})
    if verdict == "OFF-TOPIC": p["status"] = "off-topic"
    elif verdict == "EXTRACTED":
        if prior - {agent} and (agrees or disputes): p["status"] = "audited" if agrees else "disputed"
        elif p["status"] == "open": p["status"] = "extracted-1"
    json.dump(q, open("results/lit_queue.json", "w"), ensure_ascii=False, indent=1)
    gh(f"/issues/{issue}/comments", {"body": comment})
    gh(f"/issues/{issue}", {"state": "closed"}, "PATCH")
    print(f"{pid} ← {agent} {verdict}: status {p['status']}; issue #{issue} closed")


if __name__ == "__main__":
    main()
