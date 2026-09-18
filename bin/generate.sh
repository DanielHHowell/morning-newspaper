#!/usr/bin/env bash
# Run Claude Code headless as "the editor": gathers feeds/news and writes editions/DATE.body.html
set -euo pipefail
cd "$(dirname "$0")/.."
source bin/env.sh
DATE="${1:-$(date +%F)}"
TZ_NAME="$(date +%Z)"

WEATHER_DATA="$(LOCATION="$LOCATION" python3 bin/weather.py 2>&1 || echo "(weather unavailable)")"
[[ -n "$WEATHER_DATA" ]] || WEATHER_DATA="(no location configured; skip the weather strip)"
MARKETS_DATA="$(STOCKS="$STOCKS" python3 bin/markets.py 2>&1 || echo "(markets unavailable)")"
FEEDS_DATA="$(python3 bin/feeds.py 2>&1 || echo "(feeds unavailable)")"

PROMPT="$(python3 - "$DATE" "$TZ_NAME" "$READER_NAME" "$WEATHER_DATA" "$MARKETS_DATA" "$FEEDS_DATA" <<'PY'
import sys, pathlib
date, tz, name, weather, markets, feeds = sys.argv[1:7]
s = pathlib.Path("PROMPT.md").read_text()
for k, v in (("READER_NAME", name), ("TODAY", date), ("TZ_NAME", tz), ("WEATHER_DATA", weather), ("MARKETS_DATA", markets), ("FEEDS_DATA", feeds)):
    s = s.replace(k, v)
print(s)
PY
)"

"$CLAUDE_BIN" -p "$PROMPT" < /dev/null \
  --model "$MODEL" \
  --allowedTools "Read" "Write" "WebSearch" "WebFetch" "mcp__feeder" \
  --disallowedTools "Bash" "Edit" \
  --max-turns 50

test -s "editions/$DATE.body.html" || { echo "editor did not write editions/$DATE.body.html" >&2; exit 1; }
