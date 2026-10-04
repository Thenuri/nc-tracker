"""
Django settings for the NC Tracker project.

All environment-specific values (secrets, database, email, prototype mode)
come from a `.env` file via django-environ, so moving from the laptop
prototype to the APIIT server is a config change, not a code change.
See `.env.example` for every variable and its meaning.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Declare each variable's type and default. Anything without a default
# (e.g. SECRET_KEY) MUST be set in .env, otherwise Django refuses to start.
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    PROTOTYPE_MODE=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")


# --- Security -------------------------------------------------------------

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# When True: shows the "PROTOTYPE – sample data" banner and (from Phase 3)
# enables the "Who am I?" role switcher. Must be False in production.
PROTOTYPE_MODE = env("PROTOTYPE_MODE")


# --- Applications ---------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Our apps
    "accounts",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nc_tracker.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-wide templates (base.html etc.) live in /templates
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Makes PROTOTYPE_MODE available in every template
                "core.context_processors.prototype_mode",
            ],
        },
    },
]

WSGI_APPLICATION = "nc_tracker.wsgi.application"


# --- Database -------------------------------------------------------------
# SQLite on the laptop now; PostgreSQL later by changing DATABASE_URL only,
# e.g. DATABASE_URL=postgres://user:password@host:5432/nc_tracker

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}


# --- Users and passwords --------------------------------------------------

# Custom user model, set before the first migration so we can add role and
# department fields later (Phase 2) without rebuilding the database.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Email ----------------------------------------------------------------
# Prototype: console backend prints emails in the terminal.
# Later: switch EMAIL_BACKEND / EMAIL_* in .env to send from nctracker@apiit.lk.

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="nctracker@apiit.lk")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)


# --- Language and time ----------------------------------------------------

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Asia/Colombo"
USE_I18N = True
USE_TZ = True


# --- Static and uploaded files --------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # filled by `collectstatic` on the server

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"  # uploaded evidence/attachments (later phases)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
