#!/usr/bin/env bash
# generate + print, with a log. This is what launchd / cron calls.
set -euo pipefail
cd "$(dirname "$0")/.."
DATE="$(date +%F)"
exec >> "logs/$DATE.log" 2>&1
echo "== $(date) =="
bin/generate.sh "$DATE"
bin/print.sh "$DATE"
