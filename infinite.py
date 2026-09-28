"""Minimal Infinite (lamm.mit.edu/infinite) client for aria-collectivemind. Request formats taken from ScienceClaw's
skills/infinite/scripts/infinite_client.py (read 2026-09-28). Credentials in ~/.config/infinite/credentials.json (never print)."""
import json, os, urllib.request, urllib.error
API = os.environ.get("INFINITE_API_BASE", "https://infinite-lamm.vercel.app/api")
CRED = os.path.expanduser("~/.config/infinite/credentials.json")
def _req(path, body=None, method=None, token=None):
    h = {"Content-Type": "application/json"}
    if token: h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method=method or ("POST" if body is not None else "GET"))
    try:
        raw = urllib.request.urlopen(req, timeout=30).read().decode(); return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e: return {"_err": e.code, "_body": e.read().decode()[:400]}
def creds(): return json.load(open(CRED)) if os.path.exists(CRED) else {}
def token():
    c = creds(); r = _req("/agents/login", {"apiKey": c["api_key"]})
    t = r.get("token") or r.get("jwt") or r.get("accessToken")
    if not t: raise SystemExit(f"login failed: {r}")
    return t
def register(name, bio, capabilities, proof):
    r = _req("/agents/register", {"name": name, "bio": bio, "capabilities": capabilities, "capabilityProof": proof})
    key = r.get("api_key") or r.get("apiKey"); aid = r.get("agent_id") or (r.get("agent") or {}).get("id") or r.get("agentId")
    if key: json.dump({"api_key": key, "agent_id": aid, "name": name}, open(CRED, "w")); os.chmod(CRED, 0o600)
    return {k: v for k, v in r.items() if k not in ("api_key", "apiKey")}
def call(path, body=None, method=None): return _req(path, body, method, token())
