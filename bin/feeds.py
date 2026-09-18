#!/usr/bin/env python3
"""Fetch recent posts from RSS/Atom feeds listed in feeds.opml (Feeder export) or feeds.txt (one URL per line).
No third-party deps. Prints plain text grouped by feed for the editor prompt.
Usage: feeds.py [opml-or-txt path] [hours]   (defaults: feeds.opml, else feeds.txt; 24h)"""
import sys, os, re, html, json, pathlib, datetime, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else next((p for p in (ROOT/"feeds.opml", ROOT/"feeds.txt") if p.exists()), None)
hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
if not path:
    print("(no feeds configured: export OPML from Feeder to feeds.opml, or list URLs in feeds.txt)"); sys.exit(0)

feeds = []  # (folder, title, url)
if path.suffix.lower() == ".opml":
    def walk(node, folder=""):
        for o in node.findall("outline"):
            if o.get("xmlUrl"):
                feeds.append((folder, o.get("title") or o.get("text") or o.get("xmlUrl"), o.get("xmlUrl")))
            else:
                walk(o, o.get("text") or o.get("title") or folder)
    walk(ET.parse(path).getroot().find("body"))
else:
    feeds = [("", u.strip(), u.strip()) for u in path.read_text().splitlines() if u.strip() and not u.startswith("#")]

since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}

def when(s):
    if not s: return None
    try: return parsedate_to_datetime(s)
    except Exception: pass
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except Exception: return None

def clean(s, n=40):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return " ".join(s.split()[:n])

def fetch(feed):
    folder, title, url = feed
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MorningNewspaper/1.0 (+rss reader)"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=15).read())
    except Exception as e:
        return folder, title, None, f"error: {type(e).__name__}"
    items = []
    ch = root.find("channel")
    if ch is not None:  # RSS 2.0
        title = ch.findtext("title") or title
        for it in ch.findall("item"):
            d = when(it.findtext("pubDate") or it.findtext("dc:date", namespaces=NS))
            items.append((d, clean(it.findtext("title"), 30), it.findtext("link") or "", clean(it.findtext("description"))))
    else:  # Atom
        title = root.findtext("atom:title", namespaces=NS) or title
        for e in root.findall("atom:entry", NS):
            d = when(e.findtext("atom:published", namespaces=NS) or e.findtext("atom:updated", namespaces=NS))
            link = next((l.get("href") for l in e.findall("atom:link", NS) if l.get("rel") in (None, "alternate")), "")
            items.append((d, clean(e.findtext("atom:title", namespaces=NS), 30), link, clean(e.findtext("atom:summary", namespaces=NS) or e.findtext("atom:content", namespaces=NS))))
    recent = sorted([i for i in items if i[0] and i[0] >= since], key=lambda i: i[0], reverse=True)[:8]
    return folder, title, recent, None

with ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(fetch, feeds))

total = 0
cache = {}
for folder, title, recent, err in results:
    for d, t, link, summ in (recent or []):
        cache[link] = {"feed": title, "title": t, "date": d.isoformat()}
try:
    (ROOT / "editions").mkdir(exist_ok=True)
    json.dump(cache, open(ROOT / "editions" / "feeds-cache.json", "w"))
except Exception:
    pass
for folder, title, recent, err in sorted(results, key=lambda r: (r[0], r[1])):
    if err: print(f"## {title} ({err})"); continue
    if not recent: continue
    print(f"## {title}" + (f"  [folder: {folder}]" if folder else ""))
    for d, t, link, summ in recent:
        total += 1
        print(f"- {t} ({d.astimezone().strftime('%a %H:%M')}) — {summ}\n  url: {link}")
print(f"\n({total} posts from {len(feeds)} feeds in the last {hours}h)")
