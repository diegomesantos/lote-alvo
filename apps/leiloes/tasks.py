import logging
from pathlib import Path

from django.utils import timezone

from .analise_juridica import analisar_imovel_avulso, analisar_imovel_caixa
from .caixa_csv import (
    ESTADOS,
    baixar_csv_caixa,
    enriquecer_imoveis_caixa,
    filtrar_detalhe_pendente,
    importar_csv_caixa,
    marcar_imoveis_ausentes_como_inativos,
    ordenar_detalhe_pendente,
)
from .models import ImovelCaixa

try:
    from apps.imoveis.models import Imovel, ImovelArquivo
except ImportError:
    Imovel = None
    ImovelArquivo = None

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

    detalhe = {"atualizados": 0, "inativados": 0, "erros": []}
    if enriquecer:
        queryset = ImovelCaixa.objects.filter(
            ativo_caixa=True,
            ultima_sincronizacao_caixa__gte=sincronizacao_inicio,
        )
        if somente_pendentes_detalhe:
            queryset = filtrar_detalhe_pendente(queryset)
            queryset = ordenar_detalhe_pendente(queryset)
        else:
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
        "detalhes_inativados": detalhe["inativados"],
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
        .filter(ativo_caixa=True)
    )
    queryset = ordenar_detalhe_pendente(filtrar_detalhe_pendente(queryset))
    if max_detalhes:
        queryset = queryset[:max_detalhes]

    imoveis = list(queryset)
    detalhe = enriquecer_imoveis_caixa(imoveis, intervalo=intervalo, headless=True)
    resultado = {
        "selecionados": len(imoveis),
        "atualizados": detalhe["atualizados"],
        "inativados": detalhe["inativados"],
        "erros": detalhe["erros"],
    }
    logger.info("Enriquecimento Caixa concluído: %s", resultado)
    return resultado


def _payload_analise_task(status, mensagem, erro="", task_id=""):
    agora = timezone.now()
    return {
        "status": status,
        "mensagem": mensagem,
        "erro": erro,
        "task_id": task_id,
        "fontes": [],
        "resultado": None,
        "gerado_em": agora.isoformat(),
        "gerado_em_display": timezone.localtime(agora).strftime("%d/%m/%Y %H:%M"),
    }


@shared_task(bind=True)
def gerar_analise_juridica_caixa_task(self, imovel_id):
    """Gera a analise juridica IA fora do ciclo HTTP."""
    task_id = getattr(getattr(self, "request", None), "id", "") or ""
    try:
        imovel = ImovelCaixa.objects.get(imovel_id_caixa=imovel_id, ativo_caixa=True)
    except ImovelCaixa.DoesNotExist:
        logger.warning("Analise juridica ignorada: imovel Caixa %s nao encontrado", imovel_id)
        return {"status": "nao_encontrado", "imovel_id": imovel_id}

    try:
        resultado = analisar_imovel_caixa(imovel)
        if task_id and not resultado.get("task_id"):
            resultado["task_id"] = task_id
    except Exception as exc:
        logger.exception("Falha inesperada na task de analise juridica do imovel %s", imovel_id)
        resultado = _payload_analise_task(
            "erro",
            "Nao foi possivel concluir a analise juridica IA.",
            erro=str(exc)[:500],
            task_id=task_id,
        )

    imovel.refresh_from_db()
    detalhes = dict(imovel.detalhes or {})
    detalhes["analise_juridica_ia"] = resultado
    imovel.detalhes = detalhes
    imovel.save(update_fields=["detalhes", "atualizado_em"])

    logger.info(
        "Analise juridica IA concluida para imovel %s com status %s",
        imovel_id,
        resultado.get("status"),
    )
    return {
        "imovel_id": imovel_id,
        "status": resultado.get("status"),
        "task_id": task_id,
    }


@shared_task(bind=True)
def gerar_analise_juridica_imovel_task(self, imovel_uuid):
    """Gera a analise juridica IA para imóvel avulso (não Caixa)."""
    task_id = getattr(getattr(self, "request", None), "id", "") or ""

    if Imovel is None:
        logger.error("App imoveis nao disponivel para a task de analise juridica avulso")
        return {"status": "erro", "imovel_uuid": imovel_uuid}

    try:
        imovel = Imovel.objects.get(pk=imovel_uuid)
    except Imovel.DoesNotExist:
        logger.warning("Analise juridica avulso ignorada: imovel %s nao encontrado", imovel_uuid)
        return {"status": "nao_encontrado", "imovel_uuid": imovel_uuid}

    arquivos = list(
        ImovelArquivo.objects.filter(
            imovel=imovel, categoria__in=["matricula", "edital"]
        )
    )

    try:
        resultado = analisar_imovel_avulso(imovel, arquivos_imovel=arquivos)
        if task_id and not resultado.get("task_id"):
            resultado["task_id"] = task_id
    except Exception as exc:
        logger.exception("Falha inesperada na task de analise juridica avulso %s", imovel_uuid)
        resultado = _payload_analise_task(
            "erro",
            "Nao foi possivel concluir a analise juridica IA.",
            erro=str(exc)[:500],
            task_id=task_id,
        )

    imovel.refresh_from_db()
    imovel.analise_juridica_ia = resultado
    imovel.save(update_fields=["analise_juridica_ia", "updated_at"])

    logger.info(
        "Analise juridica IA avulso concluida para imovel %s com status %s",
        imovel_uuid,
        resultado.get("status"),
    )
    return {
        "imovel_uuid": str(imovel_uuid),
        "status": resultado.get("status"),
        "task_id": task_id,
    }
