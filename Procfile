web: PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright gunicorn config.wsgi --log-file -
worker: PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright DJANGO_SETTINGS_MODULE=config.settings.production celery -A config worker -l info --concurrency=1
beat: PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright DJANGO_SETTINGS_MODULE=config.settings.production celery -A config beat -l info
