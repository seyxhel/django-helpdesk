import os
import django
import traceback
import sys

# Ensure the demo package root is on sys.path so 'demodesk' imports correctly
# when this script is executed from demo/scripts
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demodesk.config.settings')
# ensure env var EMAIL_HOST_PASSWORD is set in the shell before running
django.setup()

from django.contrib.auth.forms import PasswordResetForm

EMAIL = 'sethpelagio20@gmail.com'
FROM_EMAIL = 'primedesk0@gmail.com'

print('Running PasswordResetForm test for', EMAIL)
f = PasswordResetForm({'email': EMAIL})
print('form.is_valid() ->', f.is_valid())
try:
    f.save(from_email=FROM_EMAIL, email_template_name='helpdesk/registration/password_reset_email.html')
    print('PasswordResetForm.save() completed without exception')
except Exception:
    print('PasswordResetForm.save() raised an exception:')
    traceback.print_exc()

print('\nDone')
