#!/usr/bin/env python3
"""Cross-channel collaboration dashboard for Collective Mind.

Reads every channel aria is active on (The Colony, Moltbook, AgentGram, Infinite, GitHub), builds one event stream of
everything OTHER agents did (comments, replies, DMs, likes, issues, wiki edits), classifies each agent by how far they
went (talked / claimed / ran something), and writes channels.json + channels.html (self-contained, open in a browser).

Usage: ./channels.py            # collect + render, print a terminal summary
       ./channels.py --render   # re-render channels.html from the last channels.json without hitting the network
"""
import json, os, re, sys, datetime, urllib.request, urllib.error, html

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
OUT_JSON = os.path.join(HERE, "channels.json"); OUT_HTML = os.path.join(HERE, "channels.html")
TEMPLATE = os.path.join(HERE, "channels_template.html")
SELF = {"aria", "aria_collectivemind", "aria-collectivemind", "nicolascepeda", "github-actions[bot]", "collective-mind-org[bot]", "abundai"}
COLONY_ID = "46290d5a-5b1b-4b96-be59-bda1bf8fe440"
AG_POST = "19423c81-8bd6-4470-bfd4-e86e7eec6815"
INF_POST = "2737412f-8aff-41c0-8b03-65ea6e97bac2"
GH_REPO = "collective-mind-org/collective-minds"
RESULT_RE = re.compile(r"(^|\n)\s*verdict:\s*(REPRODUCED|MISMATCH|PARTIAL|NOT-RUN)|RESULT:\s*(REPRODUCED|MISMATCH|NOT REPRODUCED|FAILED)|delta_pt", re.I)  # a real block or the script's printed table, not the words "CM-RESULT" or "pending"
CLAIM_RE = re.compile(r"\b(I('ll| will| can| am going to) (run|pull|take|do|reproduce|try|own)|I claim|claiming (CM-|this|it)|(taking|took) (CM-|this one|it on)|running (it|this) now)\b", re.I)

def now(): return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
def iso(s):
    if not s: return None
    s = s.replace("Z", "+00:00")
    try: d = datetime.datetime.fromisoformat(s)
    except ValueError: return None
    if d.tzinfo is None: d = d.replace(tzinfo=datetime.timezone.utc)
    return d.astimezone(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
def get(url, hdr=None):
    req = urllib.request.Request(url, headers={"Accept": "application/json", **(hdr or {})})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())
def cred(path, *keys):
    d = json.load(open(os.path.expanduser(path)))
    for k in keys: d = d[k]
    return d

def ev(channel, kind, by, at, url, text="", title="", **extra):
    return {"channel": channel, "kind": kind, "by": by or "?", "at": iso(at), "url": url, "title": (title or "")[:90],
            "text": (text or "").strip().replace("\n", " ")[:280],
            "result": bool(RESULT_RE.search(text or "")), "claim": bool(CLAIM_RE.search(text or "")), **extra}

# ----------------------------------------------------------------------------------------------------- collectors
def colony(events, threads, ch):
    import colony as C
    api = "https://thecolony.ai/api/v1"
    posts = get(f"{api}/posts?author_id={COLONY_ID}&sort=new&limit=100")
    posts = posts if isinstance(posts, list) else posts.get("items", [])
    mine = get(f"{api}/users/aria/comments").get("items", [])
    my_ids = {c["id"] for c in mine}
    my_last = {}
    for c in mine: my_last[c["post_id"]] = max(my_last.get(c["post_id"]) or "", c.get("created_at") or "")
    own = {p["id"]: p for p in posts}
    watch = dict(own)
    for c in mine: watch.setdefault(c["post_id"], None)
    ch.update(posts=len(posts), score=sum(p.get("score") or 0 for p in posts), aria_comments=len(mine),
              outreach_threads=len(watch) - len(own))
    for pid, p in watch.items():
        if p is None:
            try: p = get(f"{api}/posts/{pid}")
            except Exception: p = {"title": "(other agent's post)"}
        title = p.get("title", ""); url = f"https://thecolony.ai/post/{pid}"; page = 1; others = 0; who = set()
        while True:
            d = get(f"{api}/posts/{pid}/comments?page={page}")
            for c in d.get("items", []):
                a = (c.get("author") or {}).get("username")
                if a in SELF: continue
                reply = c.get("parent_id") in my_ids
                if pid in own or reply:
                    events.append(ev("colony", "reply" if reply else "comment", a, c.get("created_at"), url, c.get("body"), title,
                                     cid=c["id"]))
                    others += 1; who.add(a)
            if not d.get("has_more"): break
            page += 1
        to = None if pid in own else (p.get("author") or {}).get("username")
        threads.append({"channel": "colony", "kind": "post" if pid in own else "outreach", "title": title, "url": url, "own": pid in own, "to": to,
                        "score": p.get("score"), "comments_by_others": others, "agents": sorted(who),
                        "aria_last": iso(my_last.get(pid)), "last": iso(p.get("last_comment_at") or my_last.get(pid) or p.get("created_at"))})
    try:
        hist = get(f"{api}/wiki/collective-mind/history")
        for h in hist:
            a = (h.get("author") or {}).get("username")
            if a not in SELF:
                events.append(ev("colony", "wiki_edit", a, h.get("created_at"), "https://thecolony.ai/wiki/collective-mind", h.get("summary") or "", "wiki: collective-mind"))
        ch["wiki_revisions"] = len(hist)
    except Exception as e: ch.setdefault("errors", []).append(f"wiki: {e}")
    try:
        me = C.call("/users/me") or {}; ch["karma"] = me.get("karma")
        notes = C.call("/notifications") or []
        ch["unread"] = sum(1 for n in notes if isinstance(n, dict) and not n.get("is_read"))
        convs = C.call("/messages/conversations") or []
        ch["dm_conversations"] = len(convs)
        for conv in convs:
            u = (conv.get("other_user") or {}).get("username"); unread = conv.get("unread_count") or 0
            threads.append({"channel": "colony", "kind": "dm", "title": f"DM · {u}", "url": f"https://thecolony.ai/messages/{u}", "own": False, "to": u,
                            "score": None, "comments_by_others": unread, "agents": [u] if unread else [], "aria_last": None, "last": iso(conv.get("last_message_at"))})
            try:
                msgs = (C.call(f"/messages/conversations/{u}") or {}).get("messages") or []
            except Exception: msgs = []
            inbound = [m for m in msgs if ((m.get("sender") or {}).get("username")) == u]
            threads[-1]["agents"] = [u] if inbound else []; threads[-1]["comments_by_others"] = len(inbound)
            for m in inbound:
                events.append(ev("colony", "dm", u, m.get("created_at"), f"https://thecolony.ai/messages/{u}", m.get("body") or "", "DM"))
    except Exception as e: ch.setdefault("errors", []).append(f"auth: {e}")

def moltbook(events, threads, ch):
    key = cred("~/.config/moltbook/credentials.json", "api_key"); H = {"Authorization": "Bearer " + key}
    api = "https://www.moltbook.com/api/v1"
    posts = get(f"{api}/agents/me/posts", H).get("posts", [])
    ch.update(posts=len(posts), score=sum((p.get("upvotes") or p.get("score") or 0) for p in posts))
    try:
        me = get(f"{api}/agents/me", H).get("agent", {}); ch["karma"] = me.get("karma"); ch["followers"] = me.get("followerCount")
        ch["unread"] = get(f"{api}/notifications", H).get("unread_count")
    except Exception as e: ch.setdefault("errors", []).append(f"me: {e}")
    for p in posts:
        pid = p["id"]; url = f"https://www.moltbook.com/post/{pid}"; title = p.get("title", ""); who = set(); n = 0
        d = get(f"{api}/posts/{pid}/comments", H)
        stack = list(d.get("comments") or [])
        while stack:
            c = stack.pop()
            stack.extend(c.get("replies") or [])
            a = (c.get("author") or {}).get("name")
            if a in SELF: continue
            events.append(ev("moltbook", "comment", a, c.get("created_at") or c.get("createdAt"), url, c.get("content"), title, cid=c.get("id")))
            who.add(a); n += 1
        threads.append({"channel": "moltbook", "title": title, "url": url, "own": True, "score": p.get("upvotes") or p.get("score"),
                        "comments_by_others": n, "agents": sorted(who), "last": iso(p.get("updated_at") or p.get("created_at") or p.get("createdAt"))})

def agentgram(events, threads, ch):
    key = cred("~/.config/agentgram/credentials.json", "data", "apiKey"); H = {"Authorization": "Bearer " + key}
    api = "https://www.agentgram.co/api/v1"
    p = get(f"{api}/posts/{AG_POST}", H)["data"]; url = f"https://www.agentgram.co/posts/{AG_POST}"; title = p.get("title", "")
    ch.update(posts=1, score=p.get("likes"), views=p.get("view_count"))
    who = set(); n = 0
    for c in get(f"{api}/posts/{AG_POST}/comments", H)["data"]:
        a = (c.get("author") or {}).get("name")
        if a in SELF: continue
        events.append(ev("agentgram", "comment", a, c.get("created_at"), url, c.get("content"), title, cid=c.get("id"))); who.add(a); n += 1
    threads.append({"channel": "agentgram", "title": title, "url": url, "own": True, "score": p.get("likes"), "comments_by_others": n,
                    "agents": sorted(who), "last": iso(p.get("updated_at"))})
    try:
        nd = get(f"{api}/notifications", H); ch["unread"] = sum(1 for x in nd["data"] if not x.get("read"))
        ch["likes_follows"] = sum(1 for x in nd["data"] if x.get("type") in ("like", "follow"))
    except Exception as e: ch.setdefault("errors", []).append(f"notifications: {e}")

def abund(events, threads, ch):
    key = cred("~/.config/abund/credentials.json", "api_key")
    H = {"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0 (Macintosh) aria-collectivemind/1.0"}
    api = "https://api.abund.ai/api/v1"
    n = get(f"{api}/agents/me/notifications?limit=50", H)
    notes = n.get("notifications") or n.get("data") or []
    ch["unread"] = sum(1 for x in notes if not x.get("read") and not x.get("is_read"))
    for x in notes:
        a = (x.get("actor") or {}).get("handle")
        if not a or a in SELF: continue
        events.append(ev("abund", x.get("type") or "notification", a, x.get("created_at"), "https://abund.ai/agent/aria-collectivemind", str((x.get("data") or {}).get("preview") or ""), "Abund.ai"))
    reqs = get(f"{api}/requests?mine=requested", H).get("requests") or []
    ch.update(posts=len(reqs), note=f"{sum(r.get('status') == 'open' for r in reqs)} open work requests")
    for r in reqs:
        who = (r.get("assignee") or {}).get("handle")
        if who and who not in SELF:
            events.append(ev("abund", "request_" + str(r.get("status")), who, r.get("updated_at"), f"https://abund.ai/requests/{r['id']}", r.get("title") or "", "work request",
                             result=r.get("status") in ("delivered", "closed")))
        threads.append({"channel": "abund", "kind": "request", "title": f"{r.get('bounty')} cr · {r.get('title','')[:70]}", "url": f"https://abund.ai/requests/{r['id']}", "own": True,
                        "score": None, "comments_by_others": 1 if who else 0, "agents": [who] if who else [], "last": iso(r.get("updated_at"))})

def infinite_(events, threads, ch):
    import infinite as I
    url = f"https://infinite-lamm.vercel.app/post/{INF_POST}"; who = set(); n = 0
    d = I.call(f"/posts/{INF_POST}/comments")
    if "_err" in d: raise RuntimeError(f"comments {d['_err']}")
    for c in d.get("comments", []):
        a = (c.get("author") or {}).get("name") or c.get("authorName")
        if a in SELF: continue
        events.append(ev("infinite", "comment", a, c.get("createdAt") or c.get("created_at"), url, c.get("content"), "CM-BAT-R06", cid=c.get("id"))); who.add(a); n += 1
    ch.update(posts=1, note="probation until 2026-10-05")
    threads.append({"channel": "infinite", "title": "CM-BAT-R06 (Infinite)", "url": url, "own": True, "score": None, "comments_by_others": n,
                    "agents": sorted(who), "last": None})

def github(events, threads, ch):
    api = f"https://api.github.com/repos/{GH_REPO}"
    r = get(api); ch.update(stars=r.get("stargazers_count"), forks=r.get("forks_count"), watchers=r.get("subscribers_count"),
                            open_issues=r.get("open_issues_count"), pushed=iso(r.get("pushed_at")))
    issues = get(f"{api}/issues?state=all&per_page=100"); ch["issues"] = len(issues)
    for i in issues:
        a = i["user"]["login"]
        if a not in SELF:
            events.append(ev("github", "pr" if "pull_request" in i else "issue", a, i["created_at"], i["html_url"], i.get("body") or "", f"#{i['number']} {i['title']}"))
    for c in get(f"{api}/issues/comments?per_page=100"):
        a = c["user"]["login"]
        if a not in SELF:
            events.append(ev("github", "issue_comment", a, c["created_at"], c["html_url"], c.get("body") or "", c["issue_url"].rsplit("/", 1)[-1]))
    for f in get(f"{api}/forks"):
        events.append(ev("github", "fork", f["owner"]["login"], f["created_at"], f["html_url"], "", "fork"))
    ch["external_activity"] = sum(1 for e in events if e["channel"] == "github")

COLLECTORS = [("colony", "The Colony", colony), ("moltbook", "Moltbook", moltbook), ("agentgram", "AgentGram", agentgram),
              ("infinite", "Infinite", infinite_), ("abund", "Abund.ai", abund), ("github", "GitHub", github)]

# ----------------------------------------------------------------------------------------------------- local context
try: REVIEWED = json.load(open(os.path.join(HERE, "results", "credits.json"))).get("reviewed", {})
except Exception: REVIEWED = {}

def registry_notes():
    """Free-text status per agent from problems.md AGENTS & CAPABILITIES, and agents credited in results/CM-RESULTS-inbox.md."""
    notes, credited = {}, set()
    try:
        txt = open(os.path.join(HERE, "problems.md")).read()
        sec = txt.split("## AGENTS & CAPABILITIES", 1)[1].split("\n## ", 1)[0]
        for line in sec.splitlines():
            m = re.match(r"- ([\w.-]+) — (.*)", line.strip())
            if m: notes[m.group(1)] = m.group(2)[:220] + (" [CLAIMED]" if re.search(r"\bCLAIMED\b", m.group(2)) and "CLAIMED" not in m.group(2)[:220] else "")
    except Exception: pass
    try:
        for line in open(os.path.join(HERE, "results", "CM-RESULTS-inbox.md")):
            m = re.match(r"## .*? — ([\w.-]+) \(", line)
            if m: credited.add(m.group(1))
    except Exception: pass
    return notes, credited

def build_agents(events, notes, credited, t0):
    agents = {}
    for e in events:
        a = agents.setdefault(e["by"], {"name": e["by"], "channels": set(), "events": 0, "replies": 0, "results": 0, "claims": 0, "first": None, "last": None, "threads": set()})
        a["channels"].add(e["channel"]); a["events"] += 1
        a["replies"] += e["kind"] == "reply"; a["results"] += e["result"]; a["claims"] += e["claim"]
        if e["title"]: a["threads"].add(e["title"])
        for k, f in (("first", min), ("last", max)):
            if e["at"]: a[k] = e["at"] if a[k] is None else f(a[k], e["at"])
    out = []
    for a in agents.values():
        if a["name"] in credited or a["results"]: tier = "ran"
        elif a["name"] in REVIEWED: tier = "reviewed"
        elif a["claims"] or re.search(r"CLAIM", notes.get(a["name"], ""), re.I): tier = "claimed"
        elif a["events"] >= 3 or a["replies"] >= 1: tier = "engaged"
        else: tier = "one-off"
        last = datetime.datetime.fromisoformat(a["last"].replace("Z", "+00:00")) if a["last"] else None
        hrs = (t0 - last).total_seconds() / 3600 if last else None
        out.append({**a, "channels": sorted(a["channels"]), "threads": len(a["threads"]), "tier": tier, "hours_since": None if hrs is None else round(hrs, 1),
                    "active_24h": hrs is not None and hrs <= 24, "note": notes.get(a["name"], "")})
    order = {"ran": 0, "reviewed": 1, "claimed": 2, "engaged": 3, "one-off": 4}
    out.sort(key=lambda a: (order[a["tier"]], -(a["events"]), a["name"]))
    return out

def collect():
    t0 = now(); events, threads, channels = [], [], {}
    for key, label, fn in COLLECTORS:
        ch = channels.setdefault(key, {"label": label, "ok": True})
        try: fn(events, threads, ch)
        except Exception as e:
            ch["ok"] = False; ch.setdefault("errors", []).append(str(e)[:200]); print(f"{label}: {e}", file=sys.stderr)
    seen = set(); uniq = []
    for e in sorted(events, key=lambda e: e["at"] or "", reverse=True):
        k = (e["channel"], e.get("cid") or e["url"], e["by"], e["at"])
        if k in seen: continue
        seen.add(k); uniq.append(e)
    events = uniq
    notes, credited = registry_notes()
    agents = build_agents(events, notes, credited, t0)
    for key, ch in channels.items():
        mine = [e for e in events if e["channel"] == key]
        ch["events"] = len(mine); ch["agents"] = len({e["by"] for e in mine})
        ch["active_24h"] = len({e["by"] for e in mine if e["at"] and (t0 - datetime.datetime.fromisoformat(e["at"].replace("Z", "+00:00"))).total_seconds() <= 86400})
        ch["last"] = max((e["at"] for e in mine if e["at"]), default=None)
    needs = sorted(f[:-3] for f in os.listdir(os.path.join(HERE, "needs")) if f.endswith(".md") and f != "TEMPLATE.md")
    totals = {"agents": len(agents), "active_24h": sum(a["active_24h"] for a in agents), "ran": sum(a["tier"] == "ran" for a in agents), "reviewed": sum(a["tier"] == "reviewed" for a in agents),
              "claimed": sum(a["tier"] == "claimed" for a in agents), "events": len(events), "events_24h": sum(1 for e in events if e["at"] and (t0 - datetime.datetime.fromisoformat(e["at"].replace("Z", "+00:00"))).total_seconds() <= 86400),
              "unread": sum((ch.get("unread") or 0) for ch in channels.values()), "results_by_others": len(credited),
              "channels_live": sum(ch["ok"] for ch in channels.values()), "needs_open": len(needs)}
    return {"generated": t0.isoformat().replace("+00:00", "Z"), "totals": totals, "channels": channels, "agents": agents,
            "threads": sorted(threads, key=lambda t: (-(t["comments_by_others"]), t["last"] or ""), reverse=False), "events": events, "needs": needs}

def render(data):
    tpl = open(TEMPLATE).read()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    open(OUT_HTML, "w").write(tpl.replace("/*DATA*/null", payload))

def summary(d):
    t = d["totals"]
    print(f"{d['generated']}  channels live {t['channels_live']}/{len(d['channels'])}  agents {t['agents']} (active 24h {t['active_24h']}, ran {t['ran']}, claimed {t['claimed']})  "
          f"events {t['events']} ({t['events_24h']} in 24h)  unread {t['unread']}  results by others {t['results_by_others']}")
    for k, ch in d["channels"].items():
        st = "ok " if ch["ok"] else "ERR"
        print(f"  {st} {ch['label']:<10} agents={ch.get('agents',0):<3} events={ch.get('events',0):<4} active24h={ch.get('active_24h',0):<3} unread={ch.get('unread') if ch.get('unread') is not None else '-':<4} last={ch.get('last') or '-'}"
              + (f"  {'; '.join(ch['errors'])}" if ch.get("errors") else ""))
    print("  agents:")
    for a in d["agents"]:
        print(f"    {a['tier']:<8} {a['name']:<20} {','.join(a['channels']):<26} events={a['events']:<3} last={a['last'] or '-'}")
    print(f"  wrote {OUT_HTML}")

if __name__ == "__main__":
    if "--render" in sys.argv: data = json.load(open(OUT_JSON))
    else:
        data = collect(); json.dump(data, open(OUT_JSON, "w"), indent=0)
    render(data); summary(data)
