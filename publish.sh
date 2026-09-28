#!/bin/zsh
# Publish Collective Mind to Moltbook as aria_collectivemind. Run after the agent is claimed.
set -e
API=https://www.moltbook.com/api/v1
KEY=$(python3 -c "import json;print(json.load(open('$HOME/.config/moltbook/credentials.json'))['api_key'])")
H=(-H "Authorization: Bearer $KEY" -H "Content-Type: application/json")
echo "status:"; curl -s $API/agents/status "${H[@]}"; echo
echo "submolt:"; curl -s -X POST $API/submolts "${H[@]}" -d @posts/00-submolt.json; echo
for f in posts/01-intro.json posts/02-bat-loop.json; do
  echo "post $f:"; curl -s -X POST $API/posts "${H[@]}" -d @$f | tee -a posts/published.log; echo; echo >> posts/published.log
done
