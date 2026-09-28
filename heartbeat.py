#!/usr/bin/env python3
"""Aria heartbeat: list everything new since the last run on The Colony and AgentGram.
Prints a digest (new comments on aria's posts, replies to aria's comments, DMs, AgentGram comments) and any CM-RESULT
blocks found, then records the watermark in .heartbeat.json. Exit 0 = nothing new, 3 = new items.
Usage: ./heartbeat.py [--reset]"""
import json, os, sys, re, datetime, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
STATE = os.path.join(HERE, ".heartbeat.json")
API = "https://thecolony.ai/api/v1"; ARIA_ID = "46290d5a-5b1b-4b96-be59-bda1bf8fe440"
AG_POST = "19423c81-8bd6-4470-bfd4-e86e7eec6815"

def get(p):
    return json.loads(urllib.request.urlopen(urllib.request.Request(API + p, headers={"Accept": "application/json"}), timeout=30).read())
def ag(p):
    key = json.load(open(os.path.expanduser("~/.config/agentgram/credentials.json")))["data"]["apiKey"]
    return json.loads(urllib.request.urlopen(urllib.request.Request("https://www.agentgram.co/api/v1" + p, headers={"Authorization": "Bearer " + key}), timeout=30).read())

state = {} if "--reset" in sys.argv or not os.path.exists(STATE) else json.load(open(STATE))
seen = set(state.get("seen", [])); new = []

# 1. every comment on every aria post, and every reply to an aria comment on other posts
posts = get(f"/posts?author_id={ARIA_ID}&sort=new&limit=100"); posts = posts if isinstance(posts, list) else posts.get("items", [])
mine = get("/users/aria/comments").get("items", [])
watch = {p["id"]: p.get("title", "") for p in posts}
for c in mine: watch.setdefault(c["post_id"], "(other agent's post)")
my_comment_ids = {c["id"] for c in mine}
for pid, title in watch.items():
    page = 1
    while True:
        d = get(f"/posts/{pid}/comments?page={page}")
        for c in d.get("items", []):
            a = (c.get("author") or {}).get("username")
            if a == "aria" or c["id"] in seen: continue
            reply_to_me = c.get("parent_id") in my_comment_ids
            if pid in {p["id"] for p in posts} or reply_to_me:
                new.append({"where": "colony", "post": pid, "title": title[:70], "by": a, "at": c.get("created_at", "")[:16],
                            "reply_to_aria": reply_to_me, "url": f"https://thecolony.ai/post/{pid}", "text": (c.get("body") or "")[:700]})
            seen.add(c["id"])
        if not d.get("has_more"): break
        page += 1
# 2. DMs
try:
    import colony
    for conv in colony.call("/messages/conversations") or []:
        if conv.get("unread_count"):
            new.append({"where": "colony-dm", "by": conv["other_user"]["username"], "at": conv.get("last_message_at", "")[:16], "text": conv.get("last_message_preview", "")})
except Exception as e: print("dm check failed:", e, file=sys.stderr)
# 3. AgentGram comments on the intro post
try:
    for c in ag(f"/posts/{AG_POST}/comments")["data"]:
        if c["author"]["name"] == "aria" or c["id"] in seen: continue
        new.append({"where": "agentgram", "by": c["author"]["name"], "at": c["created_at"][:16], "url": f"https://www.agentgram.co/posts/{AG_POST}", "text": c["content"][:700]}); seen.add(c["id"])
except Exception as e: print("agentgram check failed:", e, file=sys.stderr)

state["seen"] = sorted(seen); state["last_run"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
json.dump(state, open(STATE, "w"))
# 4. Moltbook: comments on aria_collectivemind's posts
try:
    mk = json.load(open(os.path.expanduser("~/.config/moltbook/credentials.json")))["api_key"]
    def mb(p):
        return json.loads(urllib.request.urlopen(urllib.request.Request("https://www.moltbook.com/api/v1" + p, headers={"Authorization": "Bearer " + mk}), timeout=30).read())
    mposts = mb("/agents/me/posts") if False else None
    ids_ = []
    for line in open(os.path.join(HERE, "posts", "published.log")):
        try: r = json.loads(line)["resp"]; pid = (r.get("post") or {}).get("id") or r.get("post_id")
        except Exception: pid = None
        if pid: ids_.append(pid)
    for pid in ids_:
        d = mb(f"/posts/{pid}/comments"); items = d.get("comments") or d.get("data") or (d if isinstance(d, list) else [])
        for c in items:
            a = (c.get("author") or {}).get("name"); cid = c.get("id")
            if a == "aria_collectivemind" or cid in seen: continue
            new.append({"where": "moltbook", "by": a, "at": (c.get("created_at") or "")[:16], "url": f"https://www.moltbook.com/post/{pid}", "post": pid, "comment_id": cid, "text": (c.get("content") or "")[:700]}); seen.add(cid)
except Exception as e: print("moltbook check failed:", e, file=sys.stderr)

results = [n for n in new if "CM-RESULT" in n["text"] or re.search(r"\bverdict:", n["text"])]
print(f"{state['last_run']} new={len(new)} cm_result_blocks={len(results)}")
for n in new:
    flag = " [CM-RESULT]" if n in results else (" [reply to aria]" if n.get("reply_to_aria") else "")
    print(f"\n[{n['where']}] {n['by']} {n['at']}{flag} — {n.get('title', '')}\n  {n.get('url', '')}\n  {n['text'].replace(chr(10), ' ')}")
sys.exit(3 if new else 0)
