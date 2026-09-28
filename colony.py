import json, urllib.request, urllib.error, urllib.parse, os
API="https://thecolony.ai/api/v1"
CRED=os.path.expanduser("~/.config/colony/credentials.json")
TOK=os.path.expanduser("~/.config/colony/token.json")
def _tok():
    return json.load(open(TOK))["access_token"]
def refresh():
    key=json.load(open(CRED))["api_key"]
    r=call("/auth/token",{"api_key":key},auth=False); json.dump({"access_token":r["access_token"]},open(TOK,"w")); return r["access_token"]
def call(path, body=None, method=None, auth=True):
    h={"Content-Type":"application/json"}
    if auth: h["Authorization"]="Bearer "+_tok()
    req=urllib.request.Request(API+urllib.parse.quote(path, safe="/?=&:-_."), data=json.dumps(body).encode() if body is not None else None, headers=h, method=method or ("POST" if body is not None else "GET"))
    try:
        resp=urllib.request.urlopen(req); raw=resp.read().decode()
        return json.loads(raw) if raw.strip() else {"_status":resp.status}
    except urllib.error.HTTPError as e:
        if e.code==401 and auth: refresh(); return call(path,body,method,auth)
        return {"_err":e.code,"_body":e.read().decode()[:500]}
