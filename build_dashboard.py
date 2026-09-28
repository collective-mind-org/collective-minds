#!/usr/bin/env python3
"""Embed engagement.jsonl into dashboard.html between the DATA markers."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
snaps = [json.loads(l) for l in open(os.path.join(HERE, "engagement.jsonl")) if l.strip()]
path = os.path.join(HERE, "dashboard.html")
html = open(path).read()
payload = json.dumps(snaps, separators=(",", ":")).replace("</", "<\\/")
new = re.sub(r"<!--DATA-START-->.*?<!--DATA-END-->",
             lambda m: "<!--DATA-START-->\n" + payload + "\n<!--DATA-END-->", html, flags=re.S)
open(path, "w").write(new)
print(f"embedded {len(snaps)} snapshot(s) into dashboard.html (last: {snaps[-1]['ts'] if snaps else 'none'})")
