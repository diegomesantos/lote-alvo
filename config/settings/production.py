from .base import *
import dj_database_url
from decouple import config

DEBUG = False
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",")

DATABASE_URL = config("DATABASE_URL", default="")

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    ) if DATABASE_URL else {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://*.railway.app"
).split(",")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS]

USE_S3_MEDIA_STORAGE = config("USE_S3_MEDIA_STORAGE", default=False, cast=bool)

if USE_S3_MEDIA_STORAGE:
    INSTALLED_APPS += ["storages"]

    def _config_alias(*nomes, default=""):
        """Lê a 1ª variável de ambiente não-vazia entre vários nomes aceitos.

        O storage do B2 já foi configurado com nomes diferentes em ambientes
        distintos (B2_ACCESS_KEY_ID vs B2_KEY_ID, B2_S3_ENDPOINT_URL vs
        B2_ENDPOINT_URL). Aceitamos todos para não depender do nome exato.
        """
        for nome in nomes:
            valor = config(nome, default="")
            if valor:
                return valor
        return default

    AWS_ACCESS_KEY_ID = _config_alias(
        "AWS_ACCESS_KEY_ID", "B2_ACCESS_KEY_ID", "B2_KEY_ID",
    )
    AWS_SECRET_ACCESS_KEY = _config_alias(
        "AWS_SECRET_ACCESS_KEY", "B2_SECRET_ACCESS_KEY", "B2_APPLICATION_KEY",
    )
    AWS_STORAGE_BUCKET_NAME = _config_alias(
        "AWS_STORAGE_BUCKET_NAME", "B2_BUCKET_NAME",
    )
    AWS_S3_ENDPOINT_URL = _config_alias(
        "AWS_S3_ENDPOINT_URL", "B2_S3_ENDPOINT_URL", "B2_ENDPOINT_URL",
    )
    AWS_S3_REGION_NAME = _config_alias(
        "AWS_S3_REGION_NAME", "B2_REGION_NAME", default="us-east-005",
    )
    AWS_S3_ADDRESSING_STYLE = config("AWS_S3_ADDRESSING_STYLE", default="path")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = config("AWS_QUERYSTRING_AUTH", default=False, cast=bool)
    AWS_LOCATION = config("AWS_LOCATION", default="media").strip("/")
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": config("AWS_S3_CACHE_CONTROL", default="max-age=86400"),
    }
    AWS_S3_CUSTOM_DOMAIN = config("AWS_S3_CUSTOM_DOMAIN", default="")

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/{AWS_LOCATION}/"
