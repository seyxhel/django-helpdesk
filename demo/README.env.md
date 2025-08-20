demo/.env usage

This project supports a local `demo/.env` file for development convenience. The file is read automatically by the demo scripts and by `manage.py` so you don't need to export environment variables manually.

Steps
1. Copy the example and open it for editing:

   Copy-Item .\demo\.env.example .\demo\.env
   notepad .\demo\.env

2. Fill in SMTP values (for Gmail, generate an App Password and use that in `EMAIL_HOST_PASSWORD`).

3. Run the test script:

   .\venv\Scripts\Activate.ps1
   python .\demo\scripts\run_password_reset_test.py

Security
- Do not commit `demo/.env` to version control. It's already listed in `.gitignore`.
- For CI or production, use proper secret management instead of `.env` files.
