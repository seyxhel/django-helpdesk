# SMTP test without python-dotenv
import os
p = os.path.join(os.path.dirname(__file__), '..', '.env')
p = os.path.normpath(p)
print('reading', p)
conf = {}
with open(p, 'r', encoding='utf-8') as f:
    for l in f:
        l=l.strip()
        if not l or l.startswith('#'): continue
        if '=' in l:
            k,v=l.split('=',1)
            conf[k.strip()]=v.strip()
host=conf.get('EMAIL_HOST')
port=int(conf.get('EMAIL_PORT') or 587)
user=conf.get('EMAIL_HOST_USER')
pwd=conf.get('EMAIL_HOST_PASSWORD')
print('Testing SMTP',host,port,'user=',user)
import smtplib
try:
    s=smtplib.SMTP(host,port,timeout=10)
    s.set_debuglevel(1)
    s.ehlo()
    print('has starttls?', s.has_extn('starttls'))
    if s.has_extn('starttls'):
        s.starttls(); s.ehlo()
    try:
        s.login(user,pwd); print('LOGIN OK')
    except Exception as e:
        print('LOGIN FAILED:', type(e), e)
    finally:
        try: s.quit()
        except: pass
except Exception as e:
    print('SMTP TEST FAILED:', type(e), e)
