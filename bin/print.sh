#!/usr/bin/env bash
# Build the PDF for DATE and send it to the printer (CUPS locally, or email to Epson Connect).
set -euo pipefail
cd "$(dirname "$0")/.."
source bin/env.sh
DATE="${1:-$(date +%F)}"


MAX_PAGES="$MAX_PAGES" WORDS_PER_PAGE="$WORDS_PER_PAGE" FULL_MAX_WORDS="$FULL_MAX_WORDS" TRUNCATE_WORDS="$TRUNCATE_WORDS" MIN_WORDS="$MIN_WORDS" \
  "$PY" bin/reader.py "$DATE" || echo "reader failed; printing front page only" >&2
PAPER="$PAPER" CHROME_BIN="$CHROME_BIN" MAX_PAGES="$MAX_PAGES" python3 bin/build.py "$DATE"
PDF="editions/$DATE.pdf"
[[ -f "editions/$DATE.print.pdf" ]] && PDF="editions/$DATE.print.pdf"   # reversed page order (see build.py)

if [[ "${DRY_RUN:-0}" == "1" ]]; then echo "DRY_RUN=1: built $PDF, not printing"; exit 0; fi

if [[ -n "${PRINTER_EMAIL:-}" ]]; then
  python3 bin/send_email.py "$PDF"
else
  lp ${PRINTER:+-d "$PRINTER"} -o media="$PAPER" -o fit-to-page "$PDF"
fi
