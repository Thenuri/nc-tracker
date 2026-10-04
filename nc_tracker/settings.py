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
    # Third-party
    "simple_history",  # audit trail of every NC change (FR-42)
    # Our apps
    "accounts",
    "core",
    "ncs",
    "notifications",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Lets the history record which logged-in user made each change
    "simple_history.middleware.HistoryRequestMiddleware",
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
                "core.context_processors.navigation",
                # Users for the "Who am I?" switcher (prototype only)
                "accounts.context_processors.role_switcher",
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

# Prototype: the home page is where you pick "Who am I?". Later this becomes
# the Microsoft sign-in URL.
LOGIN_URL = "/"
LOGOUT_REDIRECT_URL = "/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Email ----------------------------------------------------------------
# Prototype: console backend prints emails in the terminal.
# Later: switch EMAIL_BACKEND / EMAIL_* in .env to send from nctracker@apiit.lk.

# Full address of the site, used for links in emails (UI-03).
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000").rstrip("/")

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="nctracker@apiit.lk")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)


# --- NC rules still marked [TBC] in the SRS ---------------------------------
# Defaults agreed in CLAUDE.md; change them in .env without touching code.

# FR-14: days (Mon–Fri) the receiving HoD has to validate a new NC
NC_VALIDATION_WORKING_DAYS = env.int("NC_VALIDATION_WORKING_DAYS", default=3)
# FR-26: remind the Action Owner this many days before the target date
NC_REMINDER_DAYS_BEFORE_TARGET = env.int("NC_REMINDER_DAYS_BEFORE_TARGET", default=7)
# FR-27: tell the NC Manager when an NC is this many days overdue
NC_ESCALATION_DAYS_OVERDUE = env.int("NC_ESCALATION_DAYS_OVERDUE", default=14)
# SRS 3.1: NCs within one department still need validation
NC_SAME_DEPARTMENT_NEEDS_VALIDATION = env.bool("NC_SAME_DEPARTMENT_NEEDS_VALIDATION", default=True)


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
