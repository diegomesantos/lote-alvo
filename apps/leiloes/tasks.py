import logging
from pathlib import Path

from django.utils import timezone

from .caixa_csv import (
    ESTADOS,
    baixar_csv_caixa,
    enriquecer_imoveis_caixa,
    importar_csv_caixa,
    marcar_imoveis_ausentes_como_inativos,
)
from .models import ImovelCaixa

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


def _arquivos_csv(estado="geral", todos_estados=False, destino_dir="media/caixa_csv", headless=True):
    if todos_estados:
        return [
            baixar_csv_caixa(estado=uf, destino_dir=destino_dir, headless=headless)
            for uf in ESTADOS
        ]

    return [
        baixar_csv_caixa(estado=estado, destino_dir=destino_dir, headless=headless)
    ]


def _sincronizar_csv_caixa(
    estado="geral",
    todos_estados=False,
    arquivo=None,
    destino_dir="media/caixa_csv",
    limite=None,
    inativar_ausentes=True,
    enriquecer=False,
    max_detalhes=None,
    somente_pendentes_detalhe=True,
    intervalo=1.0,
    headless=True,
):
    if limite and inativar_ausentes:
        raise ValueError("limite não pode ser usado com inativar_ausentes")

    sincronizacao_inicio = timezone.now()
    estado_normalizado = str(estado or "geral").upper()
    if estado_normalizado == "GERAL":
        estado_normalizado = "geral"

    if arquivo:
        arquivos = [Path(arquivo)]
    else:
        arquivos = _arquivos_csv(
            estado=estado_normalizado,
            todos_estados=todos_estados,
            destino_dir=destino_dir,
            headless=headless,
        )

    total_criados = 0
    total_atualizados = 0
    total_reativados = 0
    ids_importados = []

    for caminho in arquivos:
        resultado = importar_csv_caixa(caminho, limite=limite)
        ids_importados.extend(resultado["ids"])
        total_criados += resultado["criados"]
        total_atualizados += resultado["atualizados"]
        total_reativados += resultado.get("reativados", 0)

    inativados = 0
    if inativar_ausentes:
        estado_inativacao = None
        if not todos_estados and estado_normalizado != "geral":
            estado_inativacao = estado_normalizado

        inativados = marcar_imoveis_ausentes_como_inativos(
            ids_importados,
            estado=estado_inativacao,
            sincronizacao_inicio=sincronizacao_inicio,
        )

    detalhe = {"atualizados": 0, "erros": []}
    if enriquecer:
        queryset = ImovelCaixa.objects.filter(
            ativo_caixa=True,
            ultima_sincronizacao_caixa__gte=sincronizacao_inicio,
        )
        if somente_pendentes_detalhe:
            queryset = queryset.filter(detalhe_atualizado_em__isnull=True)
        queryset = queryset.order_by("estado", "cidade", "imovel_id_caixa")
        if max_detalhes:
            queryset = queryset[:max_detalhes]

        detalhe = enriquecer_imoveis_caixa(
            list(queryset),
            intervalo=intervalo,
            headless=headless,
        )

    resultado = {
        "arquivos": [str(caminho) for caminho in arquivos],
        "ids_importados": len(ids_importados),
        "criados": total_criados,
        "atualizados": total_atualizados,
        "reativados": total_reativados,
        "inativados": inativados,
        "detalhes_atualizados": detalhe["atualizados"],
        "erros_detalhes": detalhe["erros"],
    }
    logger.info("Sincronização CSV Caixa concluída: %s", resultado)
    return resultado


@shared_task
def sincronizar_leiloes_caixa_task():
    """Compatibilidade: task antiga agora usa o CSV oficial da Caixa."""
    return _sincronizar_csv_caixa(
        estado="geral",
        inativar_ausentes=True,
        enriquecer=False,
    )


@shared_task
def sincronizar_leiloes_caixa_csv_task(enriquecer=False, max_detalhes=None):
    """Sincroniza a lista geral oficial da Caixa via CSV."""
    return _sincronizar_csv_caixa(
        estado="geral",
        inativar_ausentes=True,
        enriquecer=enriquecer,
        max_detalhes=max_detalhes,
    )


@shared_task
def sincronizar_estado_caixa_task(estado, enriquecer=False, max_detalhes=None):
    """Sincroniza um único estado via CSV oficial e inativa ausentes daquela UF."""
    return _sincronizar_csv_caixa(
        estado=estado,
        inativar_ausentes=True,
        enriquecer=enriquecer,
        max_detalhes=max_detalhes,
    )


@shared_task
def enriquecer_leiloes_caixa_pendentes_task(max_detalhes=300, intervalo=1.0):
    """Busca foto, edital, matrícula e detalhes dos imóveis ativos ainda pendentes."""
    queryset = (
        ImovelCaixa.objects
        .filter(ativo_caixa=True, detalhe_atualizado_em__isnull=True)
        .order_by("estado", "cidade", "imovel_id_caixa")
    )
    if max_detalhes:
        queryset = queryset[:max_detalhes]

    imoveis = list(queryset)
    detalhe = enriquecer_imoveis_caixa(imoveis, intervalo=intervalo, headless=True)
    resultado = {
        "selecionados": len(imoveis),
        "atualizados": detalhe["atualizados"],
        "erros": detalhe["erros"],
    }
    logger.info("Enriquecimento Caixa concluído: %s", resultado)
    return resultado
