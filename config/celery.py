import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('lote_alvo')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Agendamento automático de sincronização
app.conf.beat_schedule = {
    'sincronizar-leiloes-caixa-csv-cada-6h': {
        'task': 'apps.leiloes.tasks.sincronizar_leiloes_caixa_csv_task',
        'schedule': crontab(minute=0, hour='*/6'),  # A cada 6 horas
    },
    'enriquecer-leiloes-caixa-pendentes-cada-hora': {
        'task': 'apps.leiloes.tasks.enriquecer_leiloes_caixa_pendentes_task',
        'schedule': crontab(minute=20, hour='*'),
        'args': (50, 1.0),
    },
}

app.conf.timezone = 'America/Sao_Paulo'
