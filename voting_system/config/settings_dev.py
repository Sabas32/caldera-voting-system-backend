import os

from .settings import *  # noqa: F403,F401

DEBUG = True

# Default local development to SQLite for zero-setup migrations/runs.
# Opt into PostgreSQL by setting DEV_DB=postgres in .env.
if os.getenv("DEV_DB", "sqlite").lower() != "postgres":
    DATABASES = {  # noqa: F405
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),  # noqa: F405
        }
    }
