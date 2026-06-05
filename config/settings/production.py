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

    AWS_ACCESS_KEY_ID = config(
        "AWS_ACCESS_KEY_ID",
        default=config("B2_KEY_ID", default=""),
    )
    AWS_SECRET_ACCESS_KEY = config(
        "AWS_SECRET_ACCESS_KEY",
        default=config("B2_APPLICATION_KEY", default=""),
    )
    AWS_STORAGE_BUCKET_NAME = config(
        "AWS_STORAGE_BUCKET_NAME",
        default=config("B2_BUCKET_NAME", default=""),
    )
    AWS_S3_ENDPOINT_URL = config(
        "AWS_S3_ENDPOINT_URL",
        default=config("B2_ENDPOINT_URL", default=""),
    )
    AWS_S3_REGION_NAME = config(
        "AWS_S3_REGION_NAME",
        default=config("B2_REGION_NAME", default="us-east-005"),
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
