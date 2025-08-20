#!/usr/bin/env python
"""Send password-reset emails to all active users (safe by default).

Usage:
  # dry-run (only prints what would be sent)
  python send_password_reset_all.py

  # actually send (requires explicit --send and --confirm flags)
  python send_password_reset_all.py --send --confirm

Options:
  --limit N        Limit to first N users (for testing)
  --delay S        Seconds to wait between sends (default: 1)
  --from-email E   Override FROM email (defaults to demo/ env or settings)
  --use-console    Force console backend even if SMTP is configured

This script will only send when both --send and --confirm are provided to
avoid accidental mass emails. By default it performs a dry-run.
"""
import os
import sys
import time
import argparse

# tiny .env loader (same semantics as other demo scripts)
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


def main():
    here = os.path.abspath(os.path.dirname(__file__))
    proj_root = os.path.abspath(os.path.join(here, '..'))
    load_dotenv_file(os.path.join(proj_root, '.env'))

    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true', help='Actually send emails (required with --confirm)')
    parser.add_argument('--confirm', action='store_true', help='Confirm sending (must be used with --send)')
    parser.add_argument('--limit', type=int, default=0, help='Limit to first N users')
    parser.add_argument('--delay', type=float, default=1.0, help='Seconds to wait between sends')
    parser.add_argument('--from-email', default=os.environ.get('FROM_EMAIL') or os.environ.get('EMAIL_HOST_USER'), help='From email address')
    parser.add_argument('--use-console', action='store_true', help='Force console email backend')
    parser.add_argument('--domain', default=None, help='Explicit domain to use for reset links (overrides env/Site)')
    args = parser.parse_args()

    # If user asked to force console, set env to console backend
    if args.use_console:
        os.environ['EMAIL_BACKEND'] = 'django.core.mail.backends.console.EmailBackend'

    # Require explicit confirmation to send
    if args.send and not args.confirm:
        print('Error: --send requires --confirm to actually deliver messages. Running dry-run instead.')
        args.send = False

    # Ensure demo package root is on sys.path so 'demodesk' imports correctly
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demodesk.config.settings')
    try:
        import django
    except Exception as e:
        print('Django not importable. Activate the virtualenv or install deps.')
        print(e)
        sys.exit(1)

    django.setup()

    from django.contrib.auth import get_user_model
    from django.contrib.auth.forms import PasswordResetForm
    from django.conf import settings

    User = get_user_model()

    qs = User.objects.filter(is_active=True)
    # Prefer users with non-empty emails
    qs = qs.exclude(email__exact='').exclude(email__isnull=True)
    if args.limit and args.limit > 0:
        qs = qs[: args.limit]

    emails = list(qs.values_list('email', flat=True))
    total = len(emails)
    print('Found %d active users with email' % total)
    if total == 0:
        print('No recipients found; aborting.')
        return

    sent = 0
    failed = 0
    for i, email in enumerate(emails, start=1):
        print('[%d/%d] %s' % (i, total, email))
        f = PasswordResetForm({'email': email})
        if not f.is_valid():
            print('  form invalid (no user with that email?)')
            failed += 1
            continue

        # Compute a visible reset URL for dry-run clarity (uses DEFAULT_PASSWORD_RESET_DOMAIN / Site / --domain)
        from django.conf import settings
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        # Determine domain precedence: CLI --domain, env DEFAULT_PASSWORD_RESET_DOMAIN, settings.DEFAULT_PASSWORD_RESET_DOMAIN, Site, fallback
        domain = args.domain or os.environ.get('DEFAULT_PASSWORD_RESET_DOMAIN') or getattr(settings, 'DEFAULT_PASSWORD_RESET_DOMAIN', None)
        if not domain:
            try:
                from django.contrib.sites.models import Site

                domain = Site.objects.get_current().domain
            except Exception:
                domain = '127.0.0.1:8000'

        protocol = 'https' if getattr(settings, 'USE_HTTPS_FOR_EMAILS', False) else 'http'

        # Try to resolve the actual User object for link generation
        try:
            user = User.objects.filter(email__iexact=email).first()
        except Exception:
            user = None

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_path = f"/password-reset/confirm/{uid}/{token}/"
            reset_url = f"{protocol}://{domain}{reset_path}"
        else:
            reset_url = f"{protocol}://{domain}/password-reset/"

        # trimmed host for UI (no port)
        try:
            host_only = domain.split(':', 1)[0]
        except Exception:
            host_only = domain

        if not args.send:
            print('  dry-run: would send reset email to %s' % email)
            print('    preview link ->', reset_url)

            # Also render templates to disk for manual inspection
            try:
                from django.template import loader
                out_dir = os.path.join(proj_root, 'out')
                os.makedirs(out_dir, exist_ok=True)

                context = {
                    'email': user.email if user else email,
                    'domain': domain,
                    'site_name': getattr(settings, 'SITE_NAME', domain),
                    'uid': uid if user else '',
                    'user': user,
                    'token': token if user else '',
                    'protocol': protocol,
                    'extra_email_context': {'domain_host': host_only},
                }

                # render subject, text, and html templates
                try:
                    subject = loader.render_to_string('helpdesk/registration/password_reset_subject.txt', context).strip()
                except Exception:
                    subject = f"Password reset on {context['site_name']}"

                try:
                    body_txt = loader.render_to_string('helpdesk/registration/password_reset_email.html', context)
                except Exception:
                    body_txt = f"Reset link: {reset_url}\n"

                try:
                    body_html = loader.render_to_string('helpdesk/registration/password_reset_email_html.html', context)
                except Exception:
                    body_html = ''

                safe_name = email.replace('@', '_at_').replace('.', '_')
                with open(os.path.join(out_dir, f"{safe_name}.subject.txt"), 'w', encoding='utf-8') as fh:
                    fh.write(subject + '\n')
                with open(os.path.join(out_dir, f"{safe_name}.txt"), 'w', encoding='utf-8') as fh:
                    fh.write(body_txt)
                if body_html:
                    with open(os.path.join(out_dir, f"{safe_name}.html"), 'w', encoding='utf-8') as fh:
                        fh.write(body_html)
                print('    preview files written to', out_dir)
            except Exception as e:
                print('    failed to write previews:', e)

            sent += 1
            continue

        try:
            # Determine domain for the reset link (env override, settings, or Site)
            from django.conf import settings
            domain = os.environ.get('DEFAULT_PASSWORD_RESET_DOMAIN') or getattr(settings, 'DEFAULT_PASSWORD_RESET_DOMAIN', None)
            if not domain:
                try:
                    from django.contrib.sites.models import Site

                    domain = Site.objects.get_current().domain
                except Exception:
                    domain = '127.0.0.1:8000'

            protocol = 'https' if getattr(settings, 'USE_HTTPS_FOR_EMAILS', False) else 'http'
            try:
                host_only = domain.split(':', 1)[0]
            except Exception:
                host_only = domain

            f.save(
                from_email=args.from_email,
                email_template_name='helpdesk/registration/password_reset_email.html',
                subject_template_name='helpdesk/registration/password_reset_subject.txt',
                html_email_template_name='helpdesk/registration/password_reset_email_html.html',
                domain_override=domain,
                use_https=(protocol == 'https'),
                extra_email_context={'domain_host': host_only},
            )
            print('  sent')
            sent += 1
        except Exception as e:
            print('  failed to send:', e)
            failed += 1

        if args.delay and i < total:
            time.sleep(args.delay)

    print('\nSummary: total=%d sent=%d failed=%d' % (total, sent, failed))


if __name__ == '__main__':
    main()
