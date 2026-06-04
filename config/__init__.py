# Celery initialization
# Importa apenas quando Celery estiver disponível
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery não instalado no env atual
    pass
