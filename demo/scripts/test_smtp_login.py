#!/usr/bin/env python
"""Test SMTP login using environment variables.

Reads EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from the environment and attempts to authenticate. Prints detailed errors.
"""
import os
import smtplib

HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
PORT = int(os.environ.get('EMAIL_PORT', '587'))
USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
USER = os.environ.get('EMAIL_HOST_USER')
PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

print('SMTP test parameters:')
print(' HOST=', HOST)
print(' PORT=', PORT)
print(' USE_TLS=', USE_TLS)
print(' USER=', USER)
print(' PASSWORD present? ', bool(PASSWORD))

if not USER or not PASSWORD:
    print('\nERROR: EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must be set in the environment.')
    print('Set them in your shell and re-run this script. Example (PowerShell):')
    print("$env:EMAIL_HOST_USER='you@example.com'; $env:EMAIL_HOST_PASSWORD='your-app-password'; python .\\scripts\\test_smtp_login.py")
    raise SystemExit(1)

print('\nTrying STARTTLS login (port 587) ...')
try:
    s = smtplib.SMTP(HOST, PORT, timeout=20)
    s.set_debuglevel(1)
    s.ehlo()
    if USE_TLS:
        s.starttls()
        s.ehlo()
    s.login(USER, PASSWORD)
    print('\nSTARTTLS login succeeded')
    s.quit()
except Exception as e:
    print('\nSTARTTLS login failed:')
    import traceback

    traceback.print_exc()

print('\nTrying SSL login (port 465) ...')
try:
    s = smtplib.SMTP_SSL(HOST, 465, timeout=20)
    s.set_debuglevel(1)
    s.login(USER, PASSWORD)
    print('\nSSL login succeeded')
    s.quit()
except Exception:
    print('\nSSL login failed:')
    import traceback

    traceback.print_exc()

print('\nDone')
