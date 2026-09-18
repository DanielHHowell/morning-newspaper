#!/usr/bin/env python3
"""Email a PDF to the printer's Epson Connect address via SMTP.

Env: SMTP_HOST (default smtp.gmail.com; any STARTTLS host, e.g. a cPanel mail server) SMTP_PORT (587) SMTP_USER SMTP_PASS PRINTER_EMAIL
Usage: send_email.py file.pdf
Gmail: create an App Password at https://myaccount.google.com/apppasswords and use it as SMTP_PASS.
"""
import os, smtplib, sys, pathlib
from email.message import EmailMessage

pdf = pathlib.Path(sys.argv[1])
user, pw, to = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"), os.environ.get("PRINTER_EMAIL")
if not (user and pw and to):
    sys.exit("set SMTP_USER, SMTP_PASS and PRINTER_EMAIL")

msg = EmailMessage()
msg["From"], msg["To"], msg["Subject"] = user, to, f"The Morning Newspaper {pdf.stem.replace('.print', '')}"
msg.set_content("Attached: today's edition.")  # Epson prints attachments; body text is ignored unless you enable it
msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)

with smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "587"))) as s:
    s.starttls(); s.login(user, pw); s.send_message(msg)
print(f"sent {pdf.name} to {to}")
