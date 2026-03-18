"""Django settings shared across environments."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "voting_system.apps.common",
    "voting_system.apps.organizations",
    "voting_system.apps.accounts",
    "voting_system.apps.elections",
    "voting_system.apps.tokens",
    "voting_system.apps.ballots",
    "voting_system.apps.audit",
    "voting_system.apps.analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "voting_system.apps.audit.middleware.RequestCorrelationIdMiddleware",
]

ROOT_URLCONF = "voting_system.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "voting_system.config.wsgi.application"
ASGI_APPLICATION = "voting_system.config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "EXCEPTION_HANDLER": "voting_system.apps.common.exceptions.custom_exception_handler",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": os.getenv("DRF_USER_RATE", "400/minute"),
        "token_login": os.getenv("TOKEN_LOGIN_RATE", "30/minute"),
        "token_submit": os.getenv("TOKEN_SUBMIT_RATE", "20/minute"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Voting System API",
    "DESCRIPTION": "Multi-tenant token-only voting platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SORT_OPERATIONS": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "voting_system.config.openapi.group_operations_by_domain",
    ],
    "TAGS": [
        {"name": "Authentication", "description": "Login, logout, and current user session endpoints."},
        {"name": "System Administration", "description": "System-level administrative operations."},
        {"name": "System Analytics", "description": "System dashboard and health monitoring endpoints."},
        {"name": "System Organizations", "description": "Create, list, and manage organizations from system scope."},
        {"name": "System Audit", "description": "Global cross-tenant audit trail endpoints."},
        {"name": "Organization Administration", "description": "Organization-scoped operational endpoints."},
        {"name": "Organization Dashboard", "description": "Organization dashboard KPIs and summaries."},
        {"name": "Organization Settings", "description": "Organization profile, branding, and defaults."},
        {"name": "Organization Users", "description": "Organization user and membership management."},
        {"name": "Organization Audit", "description": "Organization-level audit logs."},
        {"name": "Election Management", "description": "Election lifecycle, posts, and candidates management."},
        {"name": "Election Results", "description": "Result retrieval, export, and publication controls."},
        {"name": "Token Management", "description": "Token batch generation, revocation, reset, and exports."},
        {"name": "Public Voting", "description": "Public voter token login, ballot, status, and results APIs."},
        {"name": "Documentation", "description": "OpenAPI schema and interactive docs endpoints."},
        {"name": "Miscellaneous", "description": "Uncategorized endpoints."},
    ],
}

CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-org-id",
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()
]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

VOTER_SESSION_COOKIE = os.getenv("VOTER_SESSION_COOKIE", "voter_session")
VOTER_SESSION_MAX_AGE_SECONDS = int(os.getenv("VOTER_SESSION_MAX_AGE_SECONDS", "7200"))
TOKEN_HASH_PEPPER = os.getenv("TOKEN_HASH_PEPPER", SECRET_KEY)
TOKEN_ARCHIVE_ENCRYPTION_KEY = os.getenv("TOKEN_ARCHIVE_ENCRYPTION_KEY", "")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_BEAT_SCHEDULE = {
    "transition-elections-every-minute": {
        "task": "voting_system.apps.elections.services.run_scheduled_transitions_task",
        "schedule": timedelta(minutes=1),
    },
    "cleanup-expired-token-batches-every-minute": {
        "task": "voting_system.apps.tokens.services.run_expired_batch_cleanup_task",
        "schedule": timedelta(minutes=1),
    },
}

CACHE_BACKEND = os.getenv("CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache")
CACHES = {
    "default": {
        "BACKEND": CACHE_BACKEND,
        "LOCATION": os.getenv("CACHE_LOCATION", "voting-system-cache"),
    }
}

LOGIN_URL = "/api/v1/auth/login/"
