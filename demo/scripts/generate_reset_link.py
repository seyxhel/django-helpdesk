#!/usr/bin/env python
"""Generate a password reset link and render the email body for a given user.

Usage: python scripts/generate_reset_link.py user@example.com [--domain example.com:8000]
"""
import os
import sys
import django

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_reset_link.py user@example.com [--domain domain:port]")
        sys.exit(2)

    email = sys.argv[1]
    domain_arg = None
    if len(sys.argv) > 2 and sys.argv[2].startswith("--domain"):
        parts = sys.argv[2].split("=", 1)
        if len(parts) == 2:
            domain_arg = parts[1]

    # Ensure demo package root on path
    PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if PROJ_ROOT not in sys.path:
        sys.path.insert(0, PROJ_ROOT)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demodesk.config.settings')
    django.setup()

    from django.contrib.auth import get_user_model
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    from django.template import loader
    from django.conf import settings

    User = get_user_model()
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        print(f"No user found with email {email}")
        sys.exit(1)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Determine domain to use in the link
    domain = domain_arg or getattr(settings, 'DEFAULT_PASSWORD_RESET_DOMAIN', None)
    if not domain:
        # Try Site framework
        try:
            from django.contrib.sites.models import Site

            domain = Site.objects.get_current().domain
        except Exception:
            domain = '127.0.0.1:8000'

    protocol = 'https' if getattr(settings, 'USE_HTTPS_FOR_EMAILS', False) else 'http'
    reset_path = f"/password-reset/confirm/{uid}/{token}/"
    reset_url = f"{protocol}://{domain}{reset_path}"

    print('\nPassword reset link for user:', email)
    print(reset_url)

    # Render the email body using the configured template if available
    subject_template_name = 'registration/password_reset_subject.txt'
    email_template_name = 'helpdesk/registration/password_reset_email.html'
    context = {
        'email': user.email,
        'domain': domain,
        'site_name': getattr(settings, 'SITE_NAME', domain),
        'uid': uid,
        'user': user,
        'token': token,
        'protocol': protocol,
    }

    try:
        subject = loader.render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
    except Exception:
        subject = f"Password reset on {context['site_name']}"

    try:
        body = loader.render_to_string(email_template_name, context)
    except Exception:
        # Fallback simple body
        body = (
            f"You're receiving this email because a password reset was requested for your user account at {context['site_name']}.\n\n"
            f"Please go to the following page and choose a new password:\n\n{reset_url}\n\n"
            "If you didn't request this, you can ignore this email.\n"
        )

    print('\nSubject:')
    print(subject)
    print('\nBody (rendered):')
    print(body)

    print('\nDone')
