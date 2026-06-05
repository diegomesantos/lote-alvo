from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "crispy_forms",
    "crispy_tailwind",
    # Local
    "apps.accounts",
    "apps.imoveis",
    "apps.calculadora",
    "apps.financeiro",
    "apps.leiloes",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/kanban/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL",
    default=config("REDIS_URL", default="redis://localhost:6379/0"),
)
CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND",
    default=CELERY_BROKER_URL,
)
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_TIME_LIMIT", default=60 * 60 * 3, cast=int)
CELERY_TASK_SOFT_TIME_LIMIT = config("CELERY_TASK_SOFT_TIME_LIMIT", default=60 * 60 * 2, cast=int)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Apify Configuration
APIFY_API_TOKEN = config("APIFY_API_TOKEN", default="")
APIFY_ACTOR_ID = "l3QeUiJVEtg15dpH2"  # leadercorp/caixa-leiloes-scraper - dados reais da Caixa
APIFY_API_URL = "https://api.apify.com/v2/acts/{actor_id}/run-sync"

# IA - analise juridica sob demanda dos documentos da Caixa
AI_LEGAL_ANALYSIS_PROVIDER = config("AI_LEGAL_ANALYSIS_PROVIDER", default="openai").strip().lower()
AI_LEGAL_ANALYSIS_API_KEY = config("AI_LEGAL_ANALYSIS_API_KEY", default="")
AI_LEGAL_ANALYSIS_MODEL = config(
    "AI_LEGAL_ANALYSIS_MODEL",
    default=config("OPENAI_LEGAL_ANALYSIS_MODEL", default="gpt-5.5"),
)
AI_LEGAL_ANALYSIS_REASONING_EFFORT = config(
    "AI_LEGAL_ANALYSIS_REASONING_EFFORT",
    default=config("OPENAI_LEGAL_ANALYSIS_REASONING_EFFORT", default="medium"),
)
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
ANTHROPIC_API_VERSION = config("ANTHROPIC_API_VERSION", default="2023-06-01")
GEMINI_API_KEY = config("GEMINI_API_KEY", default=config("GOOGLE_API_KEY", default=""))

# Aliases antigos mantidos para nao quebrar ambientes ja configurados.
OPENAI_LEGAL_ANALYSIS_MODEL = AI_LEGAL_ANALYSIS_MODEL
OPENAI_LEGAL_ANALYSIS_REASONING_EFFORT = AI_LEGAL_ANALYSIS_REASONING_EFFORT
OPENAI_LEGAL_ANALYSIS_TEXT_LIMIT = config(
    "OPENAI_LEGAL_ANALYSIS_TEXT_LIMIT",
    default=50000,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS = config(
    "OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS",
    default=4500,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB = config(
    "OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB",
    default=20,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_OCR_ENABLED = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_ENABLED",
    default=True,
    cast=bool,
)
OPENAI_LEGAL_ANALYSIS_OCR_LANG = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_LANG",
    default="por+eng",
)
OPENAI_LEGAL_ANALYSIS_OCR_DPI = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_DPI",
    default=180,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_OCR_MAX_PAGES = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_MAX_PAGES",
    default=25,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_OCR_MIN_PAGE_CHARS = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_MIN_PAGE_CHARS",
    default=80,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS",
    default=45,
    cast=int,
)
