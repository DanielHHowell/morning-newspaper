# The Morning Newspaper

A personal newspaper, printed every morning at 9 while the laptop stays off.
Front page: weather and moon, a lead story, world and tech headlines, a markets table with a
why-it-moved paragraph, "on this day", and one-line picks from my RSS feeds. Then Section B:
opening excerpts of the best feed articles with QR codes to the rest, fitted to a 3-page budget.

Inspired by [newspaper.karenx.com](https://newspaper.karenx.com/), built without Grok.

## How it runs

A Claude Code cloud routine fires weekdays (`45 13 * * 1-5` UTC, 8:45am CDT, so the paper prints by ~9), clones this repo, and:

1. runs `bin/weather.py`, `bin/markets.py`, `bin/feeds.py` (all key-free public sources)
2. acts as the editor per `PROMPT.md`, writing `editions/DATE.body.html` and a ranked `picks.json`
3. `bin/reader.py` fetches the picked articles' full text and fits them to the page budget
4. `bin/build.py` renders the PDF (sandbox Chromium) and commits it to `archive/`, then pushes
5. that push triggers `.github/workflows/deliver.yml`, which reverses the pages for the face-up output
   tray and emails the PDF to the printer's Epson Connect address with `bin/send_email.py`

The cloud sandbox can't open SMTP connections (its egress proxy resets mail ports even with Network
access set to Full, which is still required for the data fetches), hence the hand-off to GitHub Actions.
Mail credentials and the printer address are GitHub Actions secrets: `SMTP_HOST`, `SMTP_USER`,
`SMTP_PASS`, `PRINTER_EMAIL`. The routine's prompt is in `cloud/ROUTINE_PROMPT.md`.

## Files

```
PROMPT.md          editor instructions: what to gather, how to lay it out
newspaper.css      broadsheet stylesheet (Letter, 3 columns, page footer, Section B styles)
template.html      html shell
feeds.txt          the RSS feeds (one URL per line; feeds.opml also accepted)
bin/weather.py     zip -> forecast + moon phase (zippopotam, Open-Meteo)
bin/markets.py     indices, BTC/ETH, stocks (Yahoo Finance, CoinGecko)
bin/feeds.py       recent posts from the feeds, plain RSS/Atom
bin/generate.sh    local only: runs the three above, then `claude -p` as the editor
bin/reader.py      picks -> article text (trafilatura) -> editions/DATE.reading.html
bin/build.py       front + Section B -> PDF; shrinks the front page to one sheet, enforces MAX_PAGES,
                   writes DATE.print.pdf with pages reversed
bin/print.sh       build, then CUPS `lp` or email to the printer if PRINTER_EMAIL is set
bin/send_email.py  SMTP helper for Epson Connect Email Print
bin/env.sh         loads config.env and fills defaults
config.env         local settings and credentials (gitignored)
```

## Run it locally

```
python3 -m venv .venv && .venv/bin/pip install trafilatura qrcode pypdf
DRY_RUN=1 bin/run.sh && open editions/$(date +%F).pdf   # build only
bin/print.sh                                            # and send to the printer
```

## Knobs (config.env or environment)

| Setting | Default | Meaning |
|---|---|---|
| `LOCATION` | zip | weather strip location |
| `STOCKS` | NVDA AAPL MSFT GOOGL AMZN META AVGO TSLA SPCX BRK-B TSM | markets table |
| `MAX_PAGES` | 3 | total pages incl. front page; also the sheet count (no duplex) |
| `FULL_MAX_WORDS` | 300 | articles up to this length print whole |
| `TRUNCATE_WORDS` | 300 | longer ones are cut near here (an excerpt), with a QR code to the rest |
| `MIN_WORDS` | 150 | skip stubs and paywalls |
| `REVERSE_PAGES` | 1 | write the page-reversed print copy |
| `MODEL` | sonnet | editor model for local runs |
