#!/usr/bin/env python3
"""Section B: full-text articles from the editor's picks, fitted to a page budget.

Reads  editions/DATE.picks.json  : [{"url","feed","title","why"}, ...]  ranked by the editor
Writes editions/DATE.reading.html : body markup for the reading section

Budget strategy (env, see config.env):
  MAX_PAGES        total pages incl. the front page (default 10) -> budget = (MAX_PAGES-1) * WORDS_PER_PAGE
  WORDS_PER_PAGE   ~800 at our 2-column 9.5pt layout (build.py also enforces MAX_PAGES on the rendered PDF)
  FULL_MAX_WORDS   articles up to this length print in full (default 2200, ~2.5 pages)
  TRUNCATE_WORDS   longer ones are cut at a paragraph boundary near this length (default 1100) + QR to the rest
  MIN_WORDS        skip stubs / paywalls / link posts below this (default 150)
Walk the picks in order; add each until the budget is spent. If the next article doesn't fit, cut it to the
remaining room when there are >= 350 words left, otherwise stop.
"""
import json, os, sys, html, pathlib, datetime, re, urllib.request
from concurrent.futures import ThreadPoolExecutor
import trafilatura, qrcode, qrcode.image.svg
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36 MorningNewspaper/1.0"}

ROOT = pathlib.Path(__file__).resolve().parent.parent
date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
picks_path = ROOT / "editions" / f"{date}.picks.json"
out_path = ROOT / "editions" / f"{date}.reading.html"
E = lambda k, d: int(os.environ.get(k) or d)
MAX_PAGES, WPP = E("MAX_PAGES", 10), E("WORDS_PER_PAGE", 800)
FULL_MAX, TRUNC, MIN_WORDS = E("FULL_MAX_WORDS", 2200), E("TRUNCATE_WORDS", 1100), E("MIN_WORDS", 150)
BUDGET = int(max(0, (MAX_PAGES - 1) * WPP) * 1.15)  # overshoot a little; build.py trims the tail to the page cap

if not picks_path.exists() or BUDGET == 0:
    out_path.write_text(""); print("no picks / zero budget: empty reading section"); sys.exit(0)
picks = json.loads(picks_path.read_text())
try:
    feed_cache = json.loads((ROOT / "editions" / "feeds-cache.json").read_text())
except Exception:
    feed_cache = {}

def nice_date(s):
    if not s: return ""
    try:
        d = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d.strftime("%b %-d, %Y")
    except Exception:
        return str(s)[:10]

def fetch(p):
    try:
        with urllib.request.urlopen(urllib.request.Request(p["url"], headers=UA), timeout=20) as r:
            d = r.read().decode(r.headers.get_content_charset() or "utf-8", "ignore")
        if not d: return p, None, None
        meta = trafilatura.extract_metadata(d)
        txt = trafilatura.extract(d, include_comments=False, include_tables=False, include_images=False,
                                  favor_precision=True, output_format="txt")
        return p, txt, meta
    except Exception:
        return p, None, None

with ThreadPoolExecutor(max_workers=8) as ex:
    fetched = list(ex.map(fetch, picks))

def paragraphs(txt, title=""):
    paras = [x.strip() for x in re.split(r"\n\s*\n|\n", txt) if len(x.strip().split()) >= 3]
    norm = lambda z: re.sub(r"\W+", " ", z).strip().lower()
    paras = [re.sub(r"\s*Read (Article|More)\s*>?\s*$", "", x) for x in paras]
    while paras and (re.match(r"^\d{1,2}(st|nd|rd|th)? \w+ \d{4}", paras[0]) or re.match(r"^\w+ \d{1,2}, \d{4}", paras[0])
                     or re.search(r"\b(listen|minute read|min read|share this|subscribe)\b", paras[0], re.I) or len(paras[0].split()) <= 4):
        paras.pop(0)  # leading date line, audio-player / read-time / share widgets
    while paras and title and (norm(paras[0]) == norm(title) or norm(title) in norm(paras[0]) and len(paras[0].split()) <= len(title.split()) + 4):
        paras.pop(0)  # article body often repeats the headline first
    while paras and (paras[-1].startswith(("-", "•")) or re.search(r"\d{4}$", paras[-1]) or len(paras[-1].split()) <= 4):
        paras.pop()  # trailing related-post link lists, tag lines, dates
    return paras

def is_subhead(para):
    return len(para.split()) <= 8 and not para.rstrip().endswith((".", ":", "?", "!", "\"", "\u201d")) and not para.startswith(("-", "•"))

def cut(paras, limit):
    """Keep whole paragraphs up to `limit` words."""
    out, n = [], 0
    for para in paras:
        w = len(para.split())
        if n + w > limit and out: break
        out.append(para); n += w
    return out, n

def qr(url):
    return qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=3, border=0).to_string().decode()

articles, used, skipped = [], 0, []
for p, txt, meta in fetched:
    if not txt:
        skipped.append((p["title"], "no text")); continue
    paras = paragraphs(txt, p.get("title", ""))
    total = sum(len(x.split()) for x in paras)
    if total < MIN_WORDS:
        skipped.append((p["title"], f"{total} words")); continue
    room = BUDGET - used
    if room < 350:
        skipped.append((p["title"], "out of room")); break
    target = total if total <= FULL_MAX else TRUNC
    target = min(target, room)
    body, n = cut(paras, target)
    truncated = n < total
    used += n
    author = (meta.author if meta and meta.author else "") or ""
    pub = nice_date((meta.date if meta and meta.date else None) or feed_cache.get(p["url"], {}).get("date"))
    src = re.sub(r"^www\.", "", re.sub(r"^https?://", "", p["url"]).split("/")[0])
    articles.append(dict(p, body=body, words=n, total=total, truncated=truncated, author=author, src=src, date=pub))
    if used >= BUDGET: break

parts = [f'<div class="reading"><div class="reading-head"><span>The Morning Newspaper · Section B</span><span>The Reading · {len(articles)} articles · ~{used} words</span><span>{date}</span></div>']
for a in articles:
    kicker = html.escape(a.get("feed", "") or a["src"])
    by = " · ".join(x for x in (html.escape(a["author"]), html.escape(a["src"]), html.escape(a["date"])) if x)
    parts.append(f'<article class="article"><h3 class="kicker">{kicker}</h3><h2>{html.escape(a["title"])}</h2>'
                 f'<p class="byline">{by}</p>' + (f'<p class="why">{html.escape(a["why"])}</p>' if a.get("why") else "") + '<div class="article-body">')
    for i, para in enumerate(a["body"]):
        if i > 0 and is_subhead(para):
            parts.append(f'<h4 class="subhead">{html.escape(para)}</h4>')
        else:
            parts.append(f'<p{" class=dropcap" if i == 0 else ""}>{html.escape(para)}</p>')
    parts.append("</div>")
    cont = (f'<div class="continued"><div class="qr">{qr(a["url"])}</div><div>Continued online (full article about {a["total"]} words). '
            f'Scan, or visit <span class="url">{html.escape(a["url"])}</span></div></div>')
    if a["truncated"]:
        parts.append(cont)
    else:
        parts.append(f'<template class="cont">{cont}</template>')  # inert; build.py swaps it in if it has to trim this article
    parts.append("</article>")
parts.append("</div>")
out_path.write_text("\n".join(parts) if articles else "")
print(f"reading section: {len(articles)} articles, {used} words (~{used / WPP:.1f} pages, budget {BUDGET}); skipped {len(skipped)}: " + "; ".join(f"{t[:40]} ({r})" for t, r in skipped))
