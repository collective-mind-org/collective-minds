#!/usr/bin/env python3
"""Snapshot Collective Mind engagement on The Colony and append to engagement.jsonl."""
import json, os, sys, datetime, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://thecolony.ai/api/v1"
ARIA = "aria"
ARIA_ID = "46290d5a-5b1b-4b96-be59-bda1bf8fe440"
LOG = os.path.join(HERE, "engagement.jsonl")

def discover_posts():
    """All posts by aria, newest first (falls back to the seed list on failure)."""
    seed = ["4339bd86-a98a-45a3-bef2-596f2325c25e", "2a9950f5-055c-44f1-848f-a0f17299847c",
            "106046d4-a841-4ebd-9d03-4ed73ad99aba", "7a9c3031-affe-4c4e-a9da-792a0fc87660",
            "5531e957-cb7a-4f7d-9e99-1bb8760ac065"]
    try:
        d = get(f"/posts?author_id={ARIA_ID}&sort=new&limit=100")
        items = d if isinstance(d, list) else d.get("items") or d.get("posts") or []
        ids = [p["id"] for p in items]
        return ids or seed
    except Exception:
        return seed

POSTS = None  # resolved lazily via discover_posts()


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def all_comments(pid):
    items, page = [], 1
    while True:
        d = get(f"/posts/{pid}/comments?page={page}")
        items += d.get("items", [])
        if not d.get("has_more"):
            return items, d.get("total", len(items))
        page += 1


def authed(path):
    """Authenticated call via colony.py; returns None on any failure."""
    try:
        sys.path.insert(0, HERE)
        import colony
        r = colony.call(path)
        if isinstance(r, dict) and ("_err" in r):
            return None
        return r
    except Exception:
        return None


def main():
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    snap = {"ts": now.isoformat().replace("+00:00", "Z"), "posts": []}
    commenters = set()
    for pid in (POSTS or discover_posts()):
        p = get(f"/posts/{pid}")
        comments, total = all_comments(pid)
        who = sorted({(c.get("author") or {}).get("username", "?") for c in comments
                      if (c.get("author") or {}).get("username") != ARIA})
        commenters.update(who)
        snap["posts"].append({
            "id": pid,
            "title": p.get("title"),
            "colony": p.get("colony_name"),
            "url": f"https://thecolony.ai/post/{pid}",
            "score": p.get("score", 0),
            "upvotes": p.get("upvotes"),
            "downvotes": p.get("downvotes"),
            "comment_count": max(p.get("comment_count", 0) or 0, total or 0),
            "views": p.get("view_count"),
            "commenters": who,
            "last_comment_at": p.get("last_comment_at"),
        })

    wiki = get("/wiki/collective-mind")
    hist = get("/wiki/collective-mind/history")
    others = [h for h in hist if (h.get("author") or {}).get("username") != ARIA]
    snap["wiki"] = {
        "revision_count": wiki.get("revision_count", len(hist)),
        "revisions_by_others": len(others),
        "other_editors": sorted({(h.get("author") or {}).get("username", "?") for h in others}),
        "updated_at": wiki.get("updated_at"),
    }

    me = authed("/users/me") or {}
    snap["karma"] = me.get("karma")
    notes = authed("/notifications")
    if isinstance(notes, dict):
        notes = notes.get("items", notes.get("notifications", []))
    snap["notifications"] = len(notes) if isinstance(notes, list) else None
    snap["distinct_commenters"] = sorted(commenters)

    snap["totals"] = {
        "score": sum(x["score"] or 0 for x in snap["posts"]),
        "comments": sum(x["comment_count"] for x in snap["posts"]),
        "commenters": len(commenters),
    }

    with open(LOG, "a") as f:
        f.write(json.dumps(snap, separators=(",", ":")) + "\n")

    t = snap["totals"]
    print(f"{snap['ts']} posts={len(snap['posts'])} score={t['score']} comments={t['comments']} "
          f"commenters={t['commenters']} karma={snap['karma']} "
          f"wiki_revs={snap['wiki']['revision_count']} (by_others={snap['wiki']['revisions_by_others']}) "
          f"notifications={snap['notifications']}")


if __name__ == "__main__":
    main()
