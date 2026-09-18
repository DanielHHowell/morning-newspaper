# Shared environment for bin/*.sh: loads config.env when present, then fills in defaults so the
# same scripts run on the laptop (config.env) and in CI (environment variables / secrets only).
[[ -f config.env ]] && source ./config.env
: "${LOCATION:=}"
: "${READER_NAME:=Daniel}"
: "${PRINTER:=}"
: "${PAPER:=Letter}"
: "${MODEL:=sonnet}"
: "${STOCKS:=NVDA AAPL MSFT GOOGL AMZN META AVGO TSLA BRK-B TSM}"
: "${MAX_PAGES:=10}"
: "${WORDS_PER_PAGE:=800}"
: "${FULL_MAX_WORDS:=2200}"
: "${TRUNCATE_WORDS:=1100}"
: "${MIN_WORDS:=150}"
: "${DRY_RUN:=0}"
: "${CLAUDE_BIN:=$(command -v claude || echo "$HOME/.local/bin/claude")}"
: "${CHROME_BIN:=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
[[ -x "${PY:-}" ]] || PY="$( [[ -x .venv/bin/python3 ]] && echo .venv/bin/python3 || echo python3 )"
export LOCATION READER_NAME PRINTER PAPER MODEL STOCKS MAX_PAGES WORDS_PER_PAGE FULL_MAX_WORDS TRUNCATE_WORDS MIN_WORDS DRY_RUN CLAUDE_BIN CHROME_BIN PY
