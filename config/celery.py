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
        # 300 imóveis/hora (~7.2k/dia) para zerar o backlog inicial de detalhes
        # mais rápido. Serial + intervalo de 1s por design anti-CAPTCHA da Caixa.
        'args': (300, 1.0),
    },
    'monitorar-fontes-cartorio-semanal': {
        'task': 'apps.calculadora.tasks.monitorar_fontes_cartorio_task',
        # As tabelas mudam pouco; monitorar semanalmente reduz ruído e carga nos TJs.
        'schedule': crontab(minute=30, hour=7, day_of_week='mon'),
    },
}

app.conf.timezone = 'America/Sao_Paulo'
