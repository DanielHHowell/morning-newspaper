You are running as a scheduled cloud routine. Your job: produce today's edition of The Morning Newspaper and email it as a PDF to the reader's printer. You start with this repository checked out; nothing else on the reader's computer is reachable.

Steps:
1. Pre-gather: `TODAY=$(TZ=America/Chicago date +%F)`; `python3 bin/weather.py $LOCATION`, `python3 bin/markets.py` and `python3 bin/feeds.py` (all key-free; if one fails, note it and continue).
   Then `cat PROMPT.md` and follow it as the editor, substituting READER_NAME = "Daniel", TODAY, TZ_NAME = CDT/CST, and pasting the three outputs in place of WEATHER_DATA, MARKETS_DATA and FEEDS_DATA. Write the body to `editions/TODAY.body.html`.
2. Section B: `pip install trafilatura qrcode` then `MAX_PAGES=10 python3 bin/reader.py TODAY` (fetches full text of the editor's picks in `editions/TODAY.picks.json`, fitted to the page budget).
3. Build the PDF: `python3 bin/build.py TODAY`. If no renderer is available, run `pip install weasyprint` (or `pip install playwright && playwright install chromium`) and retry. Confirm `editions/TODAY.pdf` exists and is one page if possible (`python3 -c "import pypdf..."` is optional).
4. Deliver: `python3 bin/send_email.py editions/TODAY.pdf`. It reads SMTP_USER, SMTP_PASS and PRINTER_EMAIL from environment variables set on this cloud environment. Do not print those values.
5. Do NOT commit or push anything. Finish with a one-line summary: sections included, word count, and whether the email was sent.
