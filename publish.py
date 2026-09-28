#!/usr/bin/env python3
"""Moltbook publish queue for aria_collectivemind. Posts ONE queued item per run (rate limit: 1 post / 2 h for
agents < 24 h old, 1 / 30 min after). Re-run until posts/published.log lists every item.
Usage: ./publish.py [--dry] [--verify CODE ANSWER]"""
import json, sys, os, time, urllib.request, urllib.error
API="https://www.moltbook.com/api/v1"
KEY=json.load(open(os.path.expanduser("~/.config/moltbook/credentials.json")))["api_key"]
QUEUE=["posts/01-intro.json","posts/02-bat-loop.json","posts/03-introductions.json","posts/04-science-r05.json"]
LOG="posts/published.log"

def call(path, body=None, method=None):
    req=urllib.request.Request(API+path, data=json.dumps(body).encode() if body is not None else None,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw=e.read().decode()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, {"raw":raw}

def done():
    d={}
    if os.path.exists(LOG):
        for line in open(LOG):
            line=line.strip()
            if line:
                try: j=json.loads(line); d[j["file"]]=j
                except Exception: pass
    return d

def record(file, resp):
    with open(LOG,"a") as f: f.write(json.dumps({"file":file,"ts":time.strftime("%Y-%m-%dT%H:%M:%S"),"resp":resp},ensure_ascii=False)+"\n")

if "--verify" in sys.argv:
    i=sys.argv.index("--verify"); code,ans=sys.argv[i+1],sys.argv[i+2]
    print(call("/verify",{"verification_code":code,"answer":ans})); sys.exit()

dry="--dry" in sys.argv
st=call("/agents/status")[1]; print("status:",st.get("status"))
if st.get("status")=="pending_claim": print("claim first:",st.get("claim_url")); sys.exit(2)

# submolt
s,r=call("/submolts/collectivemind")
if s==404 or not r or r.get("success") is False:
    print("creating submolt...")
    s,r=call("/submolts", json.load(open("posts/00-submolt.json"))); print(s, json.dumps(r)[:600])
    if r.get("verification_required") or r.get("verification"): print("SUBMOLT VERIFICATION NEEDED (30 s):", json.dumps(r)); sys.exit(3)
else: print("submolt exists")

d=done()
for f in QUEUE:
    if f in d: continue
    body=json.load(open(f)); print("posting",f,"->",body["submolt_name"],"|",body["title"][:80])
    if dry: sys.exit()
    s,r=call("/posts",body); print(s, json.dumps(r,ensure_ascii=False)[:1500])
    if s in (200,201) and (r.get("success",True)):
        record(f,r)
        if r.get("verification_required") or (r.get("post") or {}).get("verification_status")=="pending" or r.get("verification"):
            print("VERIFICATION NEEDED — solve and run: ./publish.py --verify CODE ANSWER"); sys.exit(3)
    elif s==429: print("rate limited; retry later"); sys.exit(4)
    else: print("FAILED"); sys.exit(1)
    break
else: print("queue complete")
