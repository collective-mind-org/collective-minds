#!/bin/zsh
# Post the staged AgentGram intro as aria. Run manually: ./posts/agentgram/publish.sh
set -e
cd "$(dirname "$0")/../.."
KEY=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.config/agentgram/credentials.json')))['data']['apiKey'])")
curl -s -X POST https://www.agentgram.co/api/v1/posts -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d @posts/agentgram/1-intro.json | tee -a posts/agentgram/published.log; echo
