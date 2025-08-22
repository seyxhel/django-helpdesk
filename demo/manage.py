#!/usr/bin/env python
import os
import sys
import warnings
import site

# If we haven't already re-execed with warnings suppressed, do so now.
# This ensures early-imported libraries that emit deprecation warnings
# (pkg_resources) won't print them before our filters run. We set a guard
# env var to avoid infinite re-exec loops.
if os.environ.get("DJANGO_HELPDESK_WARNINGS_SUPPRESSED") != "1":
    os.environ["DJANGO_HELPDESK_WARNINGS_SUPPRESSED"] = "1"
    # Prefer an explicit PYTHONWARNINGS setting so the interpreter suppresses
    # UserWarnings from the start. Only set if not already configured.
    os.environ.setdefault("PYTHONWARNINGS", "ignore")
    # Do NOT re-exec the process on Windows: re-execing can cause accidental
    # argument splitting for paths that contain spaces (e.g. user profile
    # paths). We rely on `demo/sitecustomize.py` and the warnings filter
    # below to suppress the deprecation message instead.

# Suppress the upcoming pkg_resources deprecation warning emitted by
# some third-party packages (for example pinax-invitations). This avoids
# noisy startup warnings while you upgrade or pin Setuptools.
# Alternatives:
# - Pin setuptools to a safe version: e.g. add `setuptools<81` to your
#   project's requirements/dev environment.
# - Upgrade or replace the package using pkg_resources (e.g. newer pinax
#   releases) to use importlib.metadata instead.
# - Export PYTHONWARNINGS='ignore' or set the env var in your shell for
#   the dev server.
# Prevent Python from adding the per-user site-packages directory to sys.path.
# This ensures the active virtualenv's site-packages take precedence and avoids
# accidentally importing packages from the global/user site which may be newer
# and trigger deprecation warnings.
try:
    site.ENABLE_USER_SITE = False
except Exception:
    pass

# Suppress the upcoming pkg_resources deprecation warning emitted by
# some third-party packages (for example pinax-invitations). This avoids
# noisy startup warnings while you upgrade or pin Setuptools.
warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API.*",
    category=UserWarning,
)


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
load_dotenv_file(os.path.join(HERE, '.env'))


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
