# The Morning Newspaper (DIY, no Grok)

A personal broadsheet, printed every morning: a front page with weather, headlines, markets,
your RSS feeds and something fun, then "Section B" with the full text of the best feed articles,
fitted to a page budget (default 10 pages). Inspired by [newspaper.karenx.com](https://newspaper.karenx.com/),
rebuilt on Claude Code + Chrome + CUPS / Epson Connect.

```
PROMPT.md          the editor's instructions (what to gather, how to lay it out)
newspaper.css      broadsheet stylesheet (Letter/A4, 3 columns)
template.html      html shell; build.py drops the CSS + body in
bin/weather.py     zip -> today/tomorrow forecast (zippopotam + Open-Meteo, no key)
bin/markets.py     indices, BTC/ETH, top stocks (Yahoo + CoinGecko, no key)
bin/feeds.py       recent posts from feeds.opml (Feeder export) or feeds.txt, plain RSS/Atom, no key
bin/generate.sh    runs the three above, then claude -p with WebSearch -> editions/DATE.body.html
bin/reader.py      editor's picks -> full article text (trafilatura) fitted to MAX_PAGES -> editions/DATE.reading.html
bin/build.py       front + reading + css -> editions/DATE.html -> editions/DATE.pdf; auto-shrinks the front page to one sheet
bin/print.sh       build + send to CUPS printer, or email to Epson Connect if PRINTER_EMAIL is set
bin/send_email.py  SMTP helper for Epson Connect Email Print
bin/run.sh         generate + print with a log (what a scheduler calls)
launchd/*.plist    local schedule (fires on wake if the Mac was asleep)
cloud/ROUTINE_PROMPT.md  prompt for a Claude Code cloud routine (laptop can be off)
config.env         your settings (gitignored)
```

## Try it now (laptop on)
```
cp feeds.txt.example feeds.txt   # or export OPML from Feeder and save as feeds.opml
python3 -m venv .venv && .venv/bin/pip install trafilatura qrcode pypdf   # for Section B
DRY_RUN=1 bin/run.sh && open editions/$(date +%F).pdf
bin/print.sh      # sends today's PDF to the Epson via CUPS
```
`LOCATION` (zip) and `STOCKS` live in `config.env`. Feeder's MCP needs a paid plan, so feeds are read directly from RSS instead.

## Option A: local schedule (Mac has to be awake or asleep-but-plugged-in)
```
cp launchd/com.daniel.morning-newspaper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.daniel.morning-newspaper.plist
```
launchd runs a missed 06:30 job as soon as the Mac wakes, so opening the lid prints the paper.
`sudo pmset repeat wakeorpoweron MTWRFSU 06:25:00` wakes a plugged-in Mac on its own.

## Option B: GitHub Actions + Epson Connect (laptop off for days)
`alternatives/github-actions-newspaper.yml` (move it to `.github/workflows/` to enable) runs every morning on a free GitHub runner (Chrome preinstalled),
builds the paper and emails the PDF to the printer. Setup, once:
1. Printer: enable Epson Connect on the ET-2800 (Setup > Epson Connect Services > Register, or Epson Smart Panel).
   You get an address like `xxxx@print.epsonconnect.com`. At epsonconnect.com turn on the Approved Senders List
   and add the Gmail address you'll send from.
2. Gmail App Password for SMTP: https://myaccount.google.com/apppasswords
3. Claude API key for the headless editor: https://console.anthropic.com/settings/keys (a few cents per edition on Sonnet).
4. Push this repo to GitHub (private) and add four Actions secrets:
   `ANTHROPIC_API_KEY`, `SMTP_USER`, `SMTP_PASS`, `PRINTER_EMAIL`.
   `gh repo create morning-newspaper --private --source . --push` then `gh secret set NAME`.
5. Test: Actions > Morning Newspaper > Run workflow. The PDF is attached to the run as an artifact and copied into
   `archive/` (the daily commit also keeps GitHub from pausing the schedule after 60 idle days).
The cron is 11:30 UTC (06:30 Austin in summer, 05:30 in winter); edit the workflow to change it.

## Option C (recommended, least setup): Claude Code cloud routine + Epson Connect
Runs on your Claude subscription, no API key, no GitHub secrets. Needs Epson Connect on the printer and
`SMTP_USER` / `SMTP_PASS` / `PRINTER_EMAIL` as environment variables on the cloud environment.
1. Printer: enable Epson Connect on the ET-2800 (Setup > Epson Connect Services > Register, or via Epson Smart Panel).
   You get an address like `xxxx@print.epsonconnect.com`. At epsonconnect.com, turn on the Approved Senders List and add your Gmail.
2. Gmail: create an App Password (myaccount.google.com/apppasswords) for SMTP sending.
3. In Claude Code run `/schedule`: create a routine, repo = this repo, cron `30 11 * * *` (06:30 America/Chicago in CDT),
   no connectors needed, prompt = contents of `cloud/ROUTINE_PROMPT.md`,
   environment variables `SMTP_USER`, `SMTP_PASS`, `PRINTER_EMAIL` on the cloud environment.
4. Run it once from https://claude.ai/code/routines and watch the printer. The cloud sandbox has no Chrome, so the
   routine has to `pip install weasyprint` or playwright for the PDF step; Option B avoids that.

## Section B budget
`MAX_PAGES` (default 10, front page included) caps the print. Articles up to `FULL_MAX_WORDS` (2200) print whole;
longer ones are cut at a paragraph near `TRUNCATE_WORDS` (1100) with a QR code to the rest. The editor ranks
12 picks; reader.py walks them in order until the budget is spent (overshooting slightly), then build.py renders
and trims the last article paragraph by paragraph until the PDF is within `MAX_PAGES`, so the last page is used
fully. Bylines show author · site · publish date. `MAX_PAGES=1` gives the front page only.

## Paper
Pages carry a "page N of M" footer. build.py also writes `DATE.print.pdf` with the page order reversed, which print.sh
sends, because the ET-2800 stacks face-up and would otherwise leave page 1 at the bottom (`REVERSE_PAGES=0` to disable).
The ET-2800 has no automatic duplex (it reports `sides-supported = one-sided`), so the morning print is
single-sided and `MAX_PAGES` is also the sheet count.

## Cost
One edition is ~40 s and a handful of tool calls on Sonnet; well under a cent of ink and a page of paper.
Switch `MODEL=opus` in config.env for nicer prose.
