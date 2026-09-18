#!/usr/bin/env python3
"""Print a compact markets table (indices, top stocks, BTC/ETH) using key-free public endpoints.
Env: STOCKS="NVDA AAPL ..." (space separated). Output is plain text for the editor prompt."""
import json, os, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh) MorningNewspaper/1.0"}
INDICES = [("^GSPC", "S&P 500"), ("^DJI", "Dow Jones"), ("^IXIC", "Nasdaq"), ("^RUT", "Russell 2000"), ("^VIX", "VIX"), ("^TNX", "10-yr yield")]
STOCKS = os.environ.get("STOCKS", "NVDA AAPL MSFT GOOGL AMZN META AVGO TSLA SPCX BRK-B TSM").split()

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        return json.load(r)

def yahoo(sym):
    m = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=5d&interval=1d")["chart"]["result"][0]["meta"]
    price = m["regularMarketPrice"]
    if "regularMarketChangePercent" in m:
        return price, m["regularMarketChangePercent"]
    prev = m.get("previousClose") or m.get("chartPreviousClose")
    return price, ((price - prev) / prev * 100 if prev else 0.0)

import urllib.parse
rows = []
for sym, name in INDICES:
    try:
        p, c = yahoo(sym); rows.append((name, f"{p:,.2f}", f"{c:+.2f}%"))
    except Exception as e:
        rows.append((name, "n/a", ""))
try:
    cg = get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true")
    rows.append(("Bitcoin", f"${cg['bitcoin']['usd']:,.0f}", f"{cg['bitcoin']['usd_24h_change']:+.2f}% (24h)"))
    rows.append(("Ethereum", f"${cg['ethereum']['usd']:,.2f}", f"{cg['ethereum']['usd_24h_change']:+.2f}% (24h)"))
except Exception:
    rows.append(("Bitcoin/Ethereum", "n/a", ""))
stock_rows = []
for s in STOCKS:
    try:
        p, c = yahoo(s); stock_rows.append((s, f"${p:,.2f}", f"{c:+.2f}%"))
    except Exception:
        stock_rows.append((s, "n/a", ""))

print("INDICES & CRYPTO (last close / change vs prior close):")
for r in rows: print(f"  {r[0]:<14}{r[1]:>12}  {r[2]}")
print("STOCKS:")
for r in stock_rows: print(f"  {r[0]:<8}{r[1]:>12}  {r[2]}")
