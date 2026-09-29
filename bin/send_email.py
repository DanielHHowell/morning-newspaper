#!/usr/bin/env python3
"""Email a PDF to the printer's Epson Connect address via SMTP.

Env: SMTP_HOST (default smtp.gmail.com; any STARTTLS/SSL host, e.g. a cPanel mail server) SMTP_PORT (587)
     SMTP_USER SMTP_PASS PRINTER_EMAIL
Usage: send_email.py file.pdf        send_email.py --test   (login only, no mail)

Works behind an HTTP(S) proxy (HTTPS_PROXY): the SMTP connection is tunneled with an HTTP CONNECT, which is
what Claude's cloud sandbox needs. Tries the configured port first, then the other of 587 (STARTTLS) / 465 (TLS).
"""
import os, smtplib, socket, ssl, sys, pathlib, urllib.parse
from email.message import EmailMessage

host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
port = int(os.environ.get("SMTP_PORT", "587"))
user, pw, to = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"), os.environ.get("PRINTER_EMAIL")
test = "--test" in sys.argv
pdf = None if test else pathlib.Path(sys.argv[1])
if not (user and pw and (to or test)):
    sys.exit("set SMTP_USER, SMTP_PASS and PRINTER_EMAIL")

def open_socket(h, p, timeout):
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not proxy:
        return socket.create_connection((h, p), timeout)
    u = urllib.parse.urlparse(proxy)
    s = socket.create_connection((u.hostname, u.port or 3128), timeout)
    s.sendall(f"CONNECT {h}:{p} HTTP/1.1\r\nHost: {h}:{p}\r\n\r\n".encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = s.recv(4096)
        if not chunk: break
        resp += chunk
    status = resp.split(b"\r\n", 1)[0]
    if b" 200" not in status:
        s.close(); raise OSError(f"proxy CONNECT {h}:{p} refused: {status.decode(errors='ignore')}")
    return s

class SMTP(smtplib.SMTP):
    def _get_socket(self, h, p, timeout):
        return open_socket(h, p, timeout)

class SMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(self, h, p, timeout):
        return self.context.wrap_socket(open_socket(h, p, timeout), server_hostname=h)

def connect(p):
    if p == 465:
        s = SMTP_SSL(host, p, timeout=40, context=ssl.create_default_context())
    else:
        s = SMTP(host, p, timeout=40); s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
    s.login(user, pw)
    return s

errors = []
for p in (port, 465 if port != 465 else 587):
    try:
        s = connect(p); break
    except Exception as e:
        errors.append(f"port {p}: {type(e).__name__}: {str(e)[:120]}")
else:
    sys.exit("SMTP failed: " + " | ".join(errors))

if test:
    s.quit(); print(f"login OK on port {p} via {host}"); sys.exit(0)

msg = EmailMessage()
msg["From"], msg["To"], msg["Subject"] = user, to, f"The Morning Newspaper {pdf.stem.replace('.print', '')}"
msg.set_content("Attached: today's edition.")
msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)
s.send_message(msg); s.quit()
print(f"sent {pdf.name} to {to} (port {p})")
