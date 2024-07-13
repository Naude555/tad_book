from .base_settings import *

ALLOWED_HOSTS = ["*"]
DEBUG = os.environ.get("DJANGO_DEBUG")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CSRF_TRUSTED_ORIGINS = [
    "http://18.190.26.177",
    # Add other origins as needed
]
