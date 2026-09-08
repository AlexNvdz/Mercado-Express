"""
Base Django settings for MercadoExpress frontend.

This project is a Django web frontend that consumes the MercadoExpress
FastAPI backend over HTTP. Django does NOT talk to PostgreSQL for business
data (catalog, orders, customers, etc). The local sqlite database configured
below is used only for Django's own internal concerns: sessions, the Django
admin, and CSRF/auth machinery.

See services/api_client.py for the HTTP layer that talks to the backend API.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Read .env from the project root if present. In Docker/production the same
# variables are expected to be provided by the environment directly.
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.cart",
    "apps.orders",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.cart.middleware.CartMiddleware",
    "apps.catalog.middleware.WishlistMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.cart.context_processors.cart",
                "apps.catalog.context_processors.wishlist",
                "apps.accounts.context_processors.auth",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# Internal Django concerns ONLY (sessions, admin, auth for staff/admin site).
# Business data lives behind the FastAPI backend, never here.
DATABASES = {
    "default": env.db(
        "DJANGO_DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", default="es")
TIME_ZONE = env("DJANGO_TIME_ZONE", default="America/Bogota")
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# MercadoExpress backend API (FastAPI) -- see ../API_CONTRACT.md
# ---------------------------------------------------------------------------
# All business operations (catalog, orders, auth, inventory, etc.) go through
# this API. Never hardcode this URL in views/templates — always read
# settings.API_BASE_URL from services/api_client.py. Env var name matches
# what API_CONTRACT.md tells Django to configure.
API_BASE_URL = env("MERCADOEXPRESS_API_BASE_URL", default="http://localhost:8000")
API_TIMEOUT_SECONDS = env.float("API_TIMEOUT_SECONDS", default=5.0)

# The backend contract is final (API_CONTRACT.md), but a live FastAPI+Postgres
# might not be running in every environment (e.g. this project's own test
# suite forces this True regardless of .env -- see conftest.py at the project
# root). Real dev/staging/production must set this False.
API_USE_MOCKS = env.bool("API_USE_MOCKS", default=False)

# Session keys used to store the backend-issued JWT token pair for the
# logged-in visitor. Django's own auth/User model is NOT the source of truth
# for customer identity -- the FastAPI backend is (see API_CONTRACT.md#authentication).
API_ACCESS_TOKEN_SESSION_KEY = "mercadoexpress_access_token"
API_REFRESH_TOKEN_SESSION_KEY = "mercadoexpress_refresh_token"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "core:home"
