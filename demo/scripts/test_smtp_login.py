#!/usr/bin/env python
"""Test SMTP login using environment variables.

Reads EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from the environment and attempts to authenticate. Prints detailed errors.
"""
import os
import smtplib

# Simple .env loader so demo/.env can be used instead of exporting env vars manually.
def load_dotenv_file(path):
    try:
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

# load demo/.env (two directories up from this script path in the repo layout)
HERE = os.path.abspath(os.path.dirname(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(HERE, '..'))
load_dotenv_file(os.path.join(PROJ_ROOT, '.env'))

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
