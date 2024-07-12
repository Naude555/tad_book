from .base_settings import *

ALLOWED_HOSTS = ["*"]
DEBUG = True  # Set to False in production

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CSRF_TRUSTED_ORIGINS = [
    "https://172.18.0.130",
    "http://172.18.0.130",
    "https://two-a-day.co.za",
    # Add other origins as needed
]
