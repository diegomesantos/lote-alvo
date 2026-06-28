import logging

from .services.cartorio_fontes import monitorar_fontes_cartorio

try:
    from celery import shared_task
except ImportError:
    def shared_task(*decorator_args, **decorator_kwargs):
        if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
            return decorator_args[0]

        def decorator(func):
            return func

        return decorator


logger = logging.getLogger(__name__)


@shared_task
def monitorar_fontes_cartorio_task(uf=None):
    """Monitora alterações nas fontes oficiais cartorárias; validação segue manual."""
    resultado = monitorar_fontes_cartorio(uf=uf)
    logger.info("Task de monitoramento cartorario concluida: %s", resultado)
    return resultado
