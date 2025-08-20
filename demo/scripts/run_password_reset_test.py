import os
import django
import traceback
import sys

# Ensure the demo package root is on sys.path so 'demodesk' imports correctly
# when this script is executed from demo/scripts
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

# Load a local .env file (demo/.env) if present so tests can run without setting shell env vars.
def load_dotenv_file(path):
    """Simple .env loader: KEY=VALUE lines, ignores comments and blank lines."""
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
                # don't overwrite existing environment variables
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        # best-effort loader; silently ignore errors to avoid breaking tests
        pass

# attempt to load demo/.env (one directory up from this script)
load_dotenv_file(os.path.join(PROJ_ROOT, '.env'))

# If SMTP credentials are not provided, force the console email backend so
# the test will render the email locally rather than attempting to send it.
if not os.environ.get('EMAIL_HOST_USER') or not os.environ.get('EMAIL_HOST_PASSWORD'):
    os.environ.setdefault('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

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
    # Determine domain to use in the email (prefer env DEFAULT_PASSWORD_RESET_DOMAIN, then Site framework)
    from django.conf import settings
    domain = os.environ.get('DEFAULT_PASSWORD_RESET_DOMAIN') or getattr(settings, 'DEFAULT_PASSWORD_RESET_DOMAIN', None)
    if not domain:
        try:
            from django.contrib.sites.models import Site

            domain = Site.objects.get_current().domain
        except Exception:
            domain = '127.0.0.1:8000'

    protocol = 'https' if getattr(settings, 'USE_HTTPS_FOR_EMAILS', False) else 'http'
    # trimmed host for UI (no port)
    try:
        host_only = domain.split(':', 1)[0]
    except Exception:
        host_only = domain

    f.save(
        from_email=FROM_EMAIL,
        email_template_name='helpdesk/registration/password_reset_email.html',
        html_email_template_name='helpdesk/registration/password_reset_email_html.html',
        domain_override=domain,
        use_https=(protocol == 'https'),
        extra_email_context={'domain_host': host_only},
    )
    print('PasswordResetForm.save() completed without exception')
except Exception:
    print('PasswordResetForm.save() raised an exception:')
    traceback.print_exc()

print('\nDone')
