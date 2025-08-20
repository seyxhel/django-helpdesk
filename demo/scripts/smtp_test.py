"""Simple SMTP connectivity and auth tester using demo/.env
Run from project root: python demo/scripts/smtp_test.py
"""
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
import smtplib
host = os.getenv('EMAIL_HOST')
port = int(os.getenv('EMAIL_PORT') or 587)
user = os.getenv('EMAIL_HOST_USER')
pwd = os.getenv('EMAIL_HOST_PASSWORD')
print('Testing SMTP', host, port, 'user=', user)
try:
    s = smtplib.SMTP(host, port, timeout=10)
    s.set_debuglevel(1)
    s.ehlo()
    print('has starttls?', s.has_extn('starttls'))
    if s.has_extn('starttls'):
        s.starttls()
        s.ehlo()
    try:
        s.login(user, pwd)
        print('LOGIN OK')
    except Exception as e:
        print('LOGIN FAILED:', type(e), e)
    finally:
        try:
            s.quit()
        except Exception:
            pass
except Exception as e:
    print('SMTP TEST FAILED:', type(e), e)
