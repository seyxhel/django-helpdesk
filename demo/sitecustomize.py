"""Project sitecustomize executed at Python startup when the script
directory is on sys.path (manages run using demo/manage.py). Use this
to disable per-user site-packages and suppress the pkg_resources
deprecation warning until dependencies are updated.
"""
import site
import warnings

try:
    site.ENABLE_USER_SITE = False
except Exception:
    pass

warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API.*",
    category=UserWarning,
)

# Optionally print a very small debug marker when starting in dev so you can
# confirm this file was imported (comment out in CI).
try:
    if __name__ == "__main__":
        print("sitecustomize loaded")
except Exception:
    pass
