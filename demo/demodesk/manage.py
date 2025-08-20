#!/usr/bin/env python
import os
import sys


# Simple .env loader (demo/.env). Does not overwrite existing env vars.
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

# attempt to load demo/.env (one directory up from this script)
HERE = os.path.abspath(os.path.dirname(__file__))
load_dotenv_file(os.path.join(HERE, '..', '.env'))


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demodesk.config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django  # noqa
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
