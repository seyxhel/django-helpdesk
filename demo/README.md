# Demo site notes

This README contains short instructions useful when running the demo site locally.

## Running the dev server with email
When testing password reset and other email features you must start the dev server in the same shell where the SMTP-related environment variables are set. Example (PowerShell):

```powershell
$env:EMAIL_HOST_USER='primedesk0@gmail.com'
$env:EMAIL_HOST_PASSWORD='<your app password here>'
$env:DEFAULT_FROM_EMAIL='primedesk0@gmail.com'
$env:HELPDESK_SMTP_DEBUG='1'   # optional, enables smtplib debug output
python manage.py runserver
```

Use a Gmail app password (recommended) if using Gmail's SMTP server.

## Generate an immediate password reset link
If you need to provide a user with a reset link immediately (for example when email delivery is delayed), use the helper script to render a one-time reset URL that points at your specified domain:

```powershell
# generate a link pointing to local dev server
python .\scripts\generate_reset_link.py user@example.com --domain=127.0.0.1:8000
```

The script prints the subject and rendered body so you can copy/paste it into a message.

## Notes
- Tokens follow Django's PASSWORD_RESET_TIMEOUT setting.
- Remove `HELPDESK_SMTP_DEBUG` or set it to `0` when you no longer need verbose SMTP protocol logs.
