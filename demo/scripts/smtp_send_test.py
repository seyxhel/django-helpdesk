# smtp_send_test.py - send a simple test email using demo/.env SMTP creds
import os
import smtplib
from email.message import EmailMessage

# locate demo/.env relative to script
here = os.path.dirname(__file__)
env_path = os.path.normpath(os.path.join(here, '..', '.env'))
conf = {}
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            conf[k.strip()] = v.strip().strip('"').strip("'")

HOST = conf.get('EMAIL_HOST')
PORT = int(conf.get('EMAIL_PORT') or 587)
USER = conf.get('EMAIL_HOST_USER')
PWD = conf.get('EMAIL_HOST_PASSWORD')
FROM = conf.get('FROM_EMAIL') or USER
TO = conf.get('TEST_TARGET') or 'sethpelagio20@gmail.com'

print('SMTP send test -> host=%s port=%s user=%s from=%s to=%s' % (HOST, PORT, USER, FROM, TO))
msg = EmailMessage()
msg['Subject'] = 'SMTP send test'
msg['From'] = FROM
msg['To'] = TO
msg.set_content('This is a test message sent by smtp_send_test.py')

try:
    s = smtplib.SMTP(HOST, PORT, timeout=20)
    s.set_debuglevel(1)
    s.ehlo()
    if s.has_extn('starttls'):
        s.starttls()
        s.ehlo()
    if USER and PWD:
        try:
            s.login(USER, PWD)
            print('SMTP login OK')
        except Exception as e:
            print('SMTP login failed:', e)
    try:
        res = s.send_message(msg)
        print('send_message result:', res)
    except Exception as e:
        print('send_message failed:', type(e), e)
    finally:
        try:
            s.quit()
        except Exception:
            pass
except Exception as e:
    print('SMTP connection failed:', type(e), e)
