web: gunicorn config.wsgi --log-file -
worker: DJANGO_SETTINGS_MODULE=config.settings.production celery -A config worker -l info --concurrency=1
beat: DJANGO_SETTINGS_MODULE=config.settings.production celery -A config beat -l info
