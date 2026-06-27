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
                "apps.imoveis.context_processors.notificacoes_usuario",
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
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
USE_S3_MEDIA_STORAGE = False
SERVE_LOCAL_MEDIA = config("SERVE_LOCAL_MEDIA", default=True, cast=bool)

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
    default=config("OPENAI_LEGAL_ANALYSIS_REASONING_EFFORT", default="high"),
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
# Página com imagem e menos texto nativo que este limite é tratada como
# escaneada (teor na imagem) e enviada para OCR mesmo passando do mínimo acima.
OPENAI_LEGAL_ANALYSIS_OCR_SCANNED_TEXT_LIMIT = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_SCANNED_TEXT_LIMIT",
    default=1500,
    cast=int,
)
OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS = config(
    "OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS",
    default=45,
    cast=int,
)

# IA - chat especialista ancorado no imovel. Cai para a config da analise
# juridica quando as variaveis AI_CHAT_* nao estao definidas.
AI_CHAT_PROVIDER = config("AI_CHAT_PROVIDER", default=AI_LEGAL_ANALYSIS_PROVIDER).strip().lower()
AI_CHAT_API_KEY = config("AI_CHAT_API_KEY", default="")
AI_CHAT_MODEL = config("AI_CHAT_MODEL", default=AI_LEGAL_ANALYSIS_MODEL)
AI_CHAT_MAX_OUTPUT_TOKENS = config("AI_CHAT_MAX_OUTPUT_TOKENS", default=1800, cast=int)
AI_CHAT_CONTEXT_TEXT_LIMIT = config("AI_CHAT_CONTEXT_TEXT_LIMIT", default=40000, cast=int)
AI_CHAT_HISTORY_LIMIT = config("AI_CHAT_HISTORY_LIMIT", default=16, cast=int)
# Timeout do cliente de IA do chat. Deve ficar ABAIXO do --timeout do gunicorn
# para a chamada falhar com erro amigável em vez de o worker ser morto.
AI_CHAT_TIMEOUT_SECONDS = config("AI_CHAT_TIMEOUT_SECONDS", default=100, cast=int)
# Chat é interativo: esforço de raciocínio mínimo para respostas rápidas/baratas.
# gpt-5.5 usa "none" como nível mínimo (o antigo "minimal" do gpt-5).
AI_CHAT_REASONING_EFFORT = config("AI_CHAT_REASONING_EFFORT", default="none")
