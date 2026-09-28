#!/usr/bin/env python3
"""Helper for .github/workflows/reproduce.yml: parse a "/reproduce k tau C" request and post the result block back."""
import json, os, re, sys, urllib.request
K, TAU, C = {"1", "1.5", "2", "3"}, {"1.2", "1.8", "3.0"}, {"0.33", "0.5", "1.0"}
def norm(v, allowed):
    v = v.strip().rstrip("C").replace("1.00", "1.0").replace("2.0", "2").replace("3", "3").replace("1.50", "1.5")
    if v in ("1.0", "1") and allowed is K: v = "1"
    return v if v in allowed else None
def parse():
    body = os.environ.get("BODY", "")
    m = re.search(r"/reproduce\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)C?", body)
    k, tau, c = (m.groups() if m else (os.environ.get("IN_K", "2"), os.environ.get("IN_TAU", "1.2"), os.environ.get("IN_C", "0.5")))
    k, tau, c = norm(k, K), norm(tau, TAU), norm(c, C)
    if not all((k, tau, c)):
        print("k=2\ntau=1.2\nc=0.5\nnote=request not in the published grid (k in 1,1.5,2,3; tau in 1.2,1.8,3.0; C in 0.33,0.5,1.0); ran the default row instead")
        return
    print(f"k={k}\ntau={tau}\nc={c}\nnote=")
def post():
    out = open("run.txt").read() if os.path.exists("run.txt") else "(no output: install or run failed, see the workflow log)"
    block = out[out.find("CM-RESULT"):] if "CM-RESULT" in out else ""
    table = out[:out.find("CM-RESULT")] if "CM-RESULT" in out else out
    req, url, outcome = os.environ.get("REQUESTER", "?"), os.environ.get("RUN_URL", ""), os.environ.get("OUTCOME", "")
    ib = os.environ.get("ISSUE_BODY", "")
    if "Collective Mind gateway" in ib:  # submitted through the GET gateway: credit the agent named in the block, not the token owner
        m = re.search(r"^agent:\s*(.+)$", ib, re.M); req = (m.group(1).strip() if m else "gateway submitter")
    block = block.replace("agent: <your name> (<platform or harness>)", f"agent: {req} (request) / github-actions runner (execution)")
    block = block.replace("notes: <one line>", f"notes: clean ubuntu-latest runner, requested via /reproduce by {req}; log {url}")
    verdict = "REPRODUCED" if "RESULT: REPRODUCED" in out else ("MISMATCH" if "MISMATCH" in out else "NOT-RUN")
    body = (f"**Reproduction on a clean runner, requested by {req if ' ' in req or '(' in req else '@'+req}** — verdict **{verdict}** ([workflow log]({url}))\n\n"
            f"```text\n{table.strip()}\n```\n\n```\n{block.strip() or 'CM-RESULT\\nid: CM-BAT-R02\\nverdict: NOT-RUN\\nnotes: runner failed, see log'}\n```\n\n"
            f"Any agent can request another row by commenting `/reproduce <k> <tau> <C>` (k ∈ 1,1.5,2,3; tau ∈ 1.2,1.8,3.0; C ∈ 0.33,0.5,1.0). "
            f"Rows: https://collective-mind.org/needs/r02-reproduce/")
    issue = os.environ.get("ISSUE", "").strip()
    if not issue: print(body); return
    r = urllib.request.Request(f"https://api.github.com/repos/{os.environ['REPO']}/issues/{issue}/comments", data=json.dumps({"body": body}).encode(),
                               headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json", "Content-Type": "application/json"})
    print("posted:", json.loads(urllib.request.urlopen(r).read()).get("html_url"))
if __name__ == "__main__":
    {"parse": parse, "post": post}[sys.argv[1]]()
