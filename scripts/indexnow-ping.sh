#!/usr/bin/env bash
# Ping IndexNow (Bing, Yandex, etc.) after Pages deploy.
# Usage: ./scripts/indexnow-ping.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="$ROOT/site"
META="$SITE/indexnow.json"
if [[ ! -f "$META" ]]; then
  echo "missing $META" >&2
  exit 1
fi
KEY=$(python3 -c "import json; print(json.load(open('$META'))['key'])")
KEY_LOC=$(python3 -c "import json; print(json.load(open('$META'))['keyLocation'])")
HOST="landjunge.github.io"
BASE="https://landjunge.github.io/tollgate"

URLS=(
  "$BASE/"
  "$BASE/de.html"
  "$BASE/docs.html"
  "$BASE/ecosystem.html"
  "$BASE/what-is-tollgate.html"
  "$BASE/blog/launch.html"
  "$BASE/blog/launch-de.html"
  "$BASE/blog/checklist.html"
  "$BASE/press/"
  "$BASE/llms.txt"
  "$BASE/sitemap.xml"
)

# Build JSON payload
PAYLOAD=$(python3 - <<PY
import json
urls = ${URLS[@]@Q}
# fix: pass via env
PY
)

python3 - <<PY
import json, urllib.request
urls = """$(printf '%s\n' "${URLS[@]}")""".strip().splitlines()
body = {
  "host": "$HOST",
  "key": "$KEY",
  "keyLocation": "$KEY_LOC",
  "urlList": urls,
}
data = json.dumps(body).encode()
req = urllib.request.Request(
  "https://api.indexnow.org/indexnow",
  data=data,
  headers={"Content-Type": "application/json; charset=utf-8"},
  method="POST",
)
try:
  with urllib.request.urlopen(req, timeout=30) as r:
    print("indexnow", r.status, r.read()[:200])
except Exception as e:
  # 200/202 ok; 422 sometimes if not yet crawlable
  print("indexnow response:", e)
  if hasattr(e, "read"):
    print(e.read()[:500])
print("urls:", len(urls))
for u in urls:
  print(" ", u)
PY
