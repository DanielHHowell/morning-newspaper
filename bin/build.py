#!/usr/bin/env python3
"""Assemble editions/DATE.body.html + newspaper.css into a full HTML page and render a PDF.

Usage: build.py [DATE]        (defaults to today, local time)
Env:   PAPER=Letter|A4  CHROME_BIN=/path/to/chrome
Renderer order: Chrome/Chromium headless -> weasyprint -> playwright (python).
"""
import datetime, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
paper = os.environ.get("PAPER", "Letter")

body_path = ROOT / "editions" / f"{date}.body.html"
reading_path = ROOT / "editions" / f"{date}.reading.html"
html_path = ROOT / "editions" / f"{date}.html"
pdf_path = ROOT / "editions" / f"{date}.pdf"
if not body_path.exists():
    sys.exit(f"missing {body_path}")

css = (ROOT / "newspaper.css").read_text().replace("size: Letter;", f"size: {paper};")
template = (ROOT / "template.html").read_text()

reading = reading_path.read_text() if reading_path.exists() else ""

def write_html(zoom, with_reading=True):
    extra = f"\n.front {{ zoom: {zoom}; }}" if zoom != 1 else ""
    body = f'<div class="front">{body_path.read_text()}</div>' + (reading if with_reading else "")
    html_path.write_text(template.replace("{{CSS}}", css + extra).replace("{{BODY}}", body).replace("{{DATE}}", date))

def page_count():
    try:  # exact, and required for weasyprint output (compressed object streams defeat the regex)
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except ImportError:
        pass
    import re
    return len(re.findall(rb"/Type\s*/Page(?![s/])", pdf_path.read_bytes()))

def chrome():
    candidates = [os.environ.get("CHROME_BIN"),
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium",
                  shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")]
    for c in candidates:
        if c and os.path.exists(c):
            r = subprocess.run([c, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                                f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                               capture_output=True, text=True)
            if pdf_path.exists():
                return True
            print(r.stderr[-800:], file=sys.stderr)
    return False

def weasy():
    try:
        from weasyprint import HTML
    except Exception:
        return False
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    return pdf_path.exists()

def playwright():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(html_path.as_uri())
        pg.pdf(path=str(pdf_path), format=paper, prefer_css_page_size=True, print_background=True)
        b.close()
    return pdf_path.exists()

def render():
    for name, fn in (("chrome", chrome), ("weasyprint", weasy), ("playwright", playwright)):
        if fn():
            return name
    return None

# Auto-fit: shrink the FRONT page until it fits on one sheet, then render with the reading section.
name = None
for zoom in (1, 0.95, 0.9, 0.85, 0.8, 0.75):
    write_html(zoom, with_reading=False)
    if pdf_path.exists(): pdf_path.unlink()
    name = render()
    if not name or page_count() <= 1:
        break
    print(f"front page at zoom {zoom}: {page_count()} pages, shrinking", file=sys.stderr)
# Hard page cap: render with the reading section; while over MAX_PAGES, trim the last article one paragraph
# at a time (swapping in its "continued online" QR block), dropping it only when almost nothing is left.
import re
max_pages = int(os.environ.get("MAX_PAGES") or 10)
ELEM = re.compile(r"<(?:p|h4)[^>]*>.*?</(?:p|h4)>", re.S)

def trim_last_article(reading):
    i = reading.rfind("<article")
    if i < 0: return None
    art = reading[i:]
    b0 = art.find('<div class="article-body">')
    b1 = art.find("</div>", b0)
    elems = ELEM.findall(art[b0:b1])
    if len(elems) <= 3:
        j = reading.rfind("</article>")
        return reading[:i] + reading[j + len("</article>"):], "dropped"
    body = art[b0:b1]
    k = body.rfind(elems[-1])
    art = art[:b0] + body[:k].rstrip() + art[b1:]
    art = re.sub(r'<template class="cont">(.*?)</template>', r"\1", art, count=1, flags=re.S)
    return reading[:i] + art, "trimmed"

steps = 0
while name and reading:
    write_html(zoom, with_reading=True)
    pdf_path.unlink()
    name = render()
    pages = page_count()
    if pages <= max_pages or "<article" not in reading or steps > 80:
        break
    reading, how = trim_last_article(reading)
    steps += 1
    print(f"{pages} pages > MAX_PAGES={max_pages}: {how} last article's tail ({steps})", file=sys.stderr)
if name:
    print(f"{pdf_path} (via {name}, front zoom {zoom}, {page_count()} pages total)")
    # Printers that stack face-up leave page 1 at the bottom; send a reversed copy so the stack reads in order.
    if os.environ.get("REVERSE_PAGES", "1") == "1":
        try:
            from pypdf import PdfReader, PdfWriter
            r = PdfReader(str(pdf_path)); w = PdfWriter()
            for pg in reversed(r.pages): w.add_page(pg)
            out = pdf_path.with_suffix(".print.pdf")
            with open(out, "wb") as f: w.write(f)
            print(f"{out} (pages reversed for face-up output trays)")
        except ImportError:
            print("pypdf not installed: no reversed copy", file=sys.stderr)
else:
    sys.exit("no PDF renderer available: install Chrome, `pip install weasyprint`, or `pip install playwright && playwright install chromium`")
