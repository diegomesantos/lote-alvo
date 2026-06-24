from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Em desenvolvimento/testes não dependemos do manifesto gerado por collectstatic.
# Isso evita falhas quando um asset novo existe em static/, mas o staticfiles.json
# local ainda está desatualizado. Produção continua usando o storage manifestado.
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
