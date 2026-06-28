import hashlib
import logging
import re

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.calculadora.models import (
    CartorioFonteEvento,
    CartorioFonteMonitorada,
    CartorioRegraExtra,
    CartorioTabela,
)


logger = logging.getLogger(__name__)

DEFAULT_MAX_BYTES = 25 * 1024 * 1024
DEFAULT_TIMEOUT = 30
USER_AGENT = (
    "LoteAlvo/1.0 (+https://lotealvo.up.railway.app; "
    "monitoramento operacional de fontes cartorarias)"
)


class FonteMonitoramentoError(Exception):
    pass


def _max_bytes():
    return int(getattr(settings, "CARTORIO_FONTE_MAX_BYTES", DEFAULT_MAX_BYTES))


def _timeout():
    return int(getattr(settings, "CARTORIO_FONTE_TIMEOUT", DEFAULT_TIMEOUT))


def _headers():
    return {
        "User-Agent": getattr(settings, "CARTORIO_FONTE_USER_AGENT", USER_AGENT),
        "Accept": "text/html,application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }


def _baixar_conteudo(url, session=None):
    session = session or requests.Session()
    response = session.get(url, headers=_headers(), timeout=_timeout(), stream=True)
    content_type = response.headers.get("content-type", "")[:180]
    etag = response.headers.get("etag", "")[:255]
    last_modified = response.headers.get("last-modified", "")[:255]

    if response.status_code >= 400:
        raise FonteMonitoramentoError(f"HTTP {response.status_code} ao acessar fonte oficial")

    max_bytes = _max_bytes()
    chunks = []
    total = 0
    truncado = False
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            truncado = True
            limite = len(chunk) - (total - max_bytes)
            if limite > 0:
                chunks.append(chunk[:limite])
            break
        chunks.append(chunk)

    conteudo = b"".join(chunks)
    return {
        "bytes": conteudo,
        "status_http": response.status_code,
        "content_type": content_type,
        "etag": etag,
        "last_modified": last_modified,
        "tamanho_bytes": min(total, max_bytes),
        "truncado": truncado,
    }


def _normalizar_html(conteudo):
    soup = BeautifulSoup(conteudo, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    texto = soup.get_text(" ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto.encode("utf-8")


def _conteudo_para_hash(conteudo, content_type):
    content_type = (content_type or "").lower()
    if "html" in content_type or "xml" in content_type:
        return _normalizar_html(conteudo)
    return conteudo


def _hash_conteudo(conteudo, content_type):
    normalizado = _conteudo_para_hash(conteudo, content_type)
    return hashlib.sha256(normalizado).hexdigest()


def _detalhe_coleta(payload):
    partes = [
        f"Status HTTP: {payload.get('status_http')}",
        f"Content-Type: {payload.get('content_type') or '-'}",
        f"Tamanho analisado: {payload.get('tamanho_bytes') or 0} bytes",
    ]
    if payload.get("etag"):
        partes.append(f"ETag: {payload['etag']}")
    if payload.get("last_modified"):
        partes.append(f"Last-Modified: {payload['last_modified']}")
    if payload.get("truncado"):
        partes.append("Conteudo truncado para limite operacional de leitura.")
    return "\n".join(partes)


def _criar_evento_mudanca(fonte, hash_anterior, hash_novo, payload):
    evento_existente = CartorioFonteEvento.objects.filter(
        fonte=fonte,
        tipo=CartorioFonteEvento.TIPO_MUDANCA,
        status=CartorioFonteEvento.STATUS_PENDENTE,
        hash_novo=hash_novo,
    ).exists()
    if evento_existente:
        return None

    return CartorioFonteEvento.objects.create(
        fonte=fonte,
        tipo=CartorioFonteEvento.TIPO_MUDANCA,
        hash_anterior=hash_anterior,
        hash_novo=hash_novo,
        status_http=payload.get("status_http"),
        content_type=payload.get("content_type", ""),
        tamanho_bytes=payload.get("tamanho_bytes"),
        mensagem="Fonte oficial alterada. Revisar tabela cartoraria antes de validar.",
        detalhe=_detalhe_coleta(payload),
    )


def _append_observacao_revalidacao(texto_atual, evento):
    marcador = f"Evento de fonte #{evento.pk}"
    if marcador in (texto_atual or ""):
        return texto_atual or ""
    linha = (
        f"Fonte oficial alterada em {timezone.localtime(evento.detectado_em).strftime('%d/%m/%Y %H:%M')}. "
        f"Tabela marcada automaticamente para revalidacao manual. {marcador}."
    )
    if texto_atual:
        return f"{texto_atual.rstrip()}\n\n{linha}"
    return linha


def _marcar_itens_da_fonte_para_revalidacao(fonte, evento):
    tabelas = CartorioTabela.objects.filter(
        uf=fonte.uf,
        fonte_url=fonte.url,
        ativo=True,
    )
    extras = CartorioRegraExtra.objects.filter(
        uf=fonte.uf,
        fonte_url=fonte.url,
        ativo=True,
    )

    tabelas_afetadas = 0
    for tabela in tabelas:
        tabela.status = CartorioTabela.STATUS_PENDENTE
        tabela.conferido_por = None
        tabela.conferido_em = None
        tabela.observacoes = _append_observacao_revalidacao(tabela.observacoes, evento)
        tabela.save(
            update_fields=[
                "status",
                "conferido_por",
                "conferido_em",
                "observacoes",
                "atualizado_em",
            ]
        )
        tabelas_afetadas += 1

    extras_afetados = 0
    for extra in extras:
        extra.status = CartorioRegraExtra.STATUS_PENDENTE
        extra.conferido_por = None
        extra.conferido_em = None
        extra.observacoes = _append_observacao_revalidacao(extra.observacoes, evento)
        extra.save(
            update_fields=[
                "status",
                "conferido_por",
                "conferido_em",
                "observacoes",
                "atualizado_em",
            ]
        )
        extras_afetados += 1

    evento.aplicacao_automatica = True
    evento.tabelas_afetadas = tabelas_afetadas
    evento.extras_afetados = extras_afetados
    evento.detalhe = (
        f"{evento.detalhe.rstrip()}\n\n"
        f"Aplicacao automatica: {tabelas_afetadas} tabela(s) e "
        f"{extras_afetados} regra(s) extra(s) marcadas para revalidacao manual."
    )
    evento.save(update_fields=["aplicacao_automatica", "tabelas_afetadas", "extras_afetados", "detalhe"])

    return {"tabelas_afetadas": tabelas_afetadas, "extras_afetados": extras_afetados}


def _criar_evento_erro(fonte, mensagem):
    evento_existente = CartorioFonteEvento.objects.filter(
        fonte=fonte,
        tipo=CartorioFonteEvento.TIPO_ERRO,
        status=CartorioFonteEvento.STATUS_PENDENTE,
        mensagem=mensagem[:260],
    ).exists()
    if evento_existente:
        return None

    return CartorioFonteEvento.objects.create(
        fonte=fonte,
        tipo=CartorioFonteEvento.TIPO_ERRO,
        mensagem=mensagem[:260],
        detalhe=mensagem,
    )


@transaction.atomic
def verificar_fonte_cartorio(fonte, session=None):
    agora = timezone.now()
    try:
        payload = _baixar_conteudo(fonte.url, session=session)
        hash_novo = _hash_conteudo(payload["bytes"], payload.get("content_type", ""))
    except (requests.RequestException, FonteMonitoramentoError) as exc:
        mensagem = f"Falha ao monitorar fonte oficial: {exc}"
        fonte.verificada_em = agora
        fonte.ultimo_erro = mensagem
        fonte.save(update_fields=["verificada_em", "ultimo_erro", "atualizado_em"])
        evento = _criar_evento_erro(fonte, mensagem)
        logger.warning("Monitoramento cartorio falhou para %s: %s", fonte, exc)
        return {
            "fonte_id": fonte.pk,
            "uf": fonte.uf,
            "status": "erro",
            "evento_id": evento.pk if evento else None,
            "mensagem": mensagem,
        }

    hash_anterior = fonte.ultimo_hash
    mudou = bool(hash_anterior and hash_anterior != hash_novo)

    fonte.ultimo_hash = hash_novo
    fonte.ultimo_status_http = payload.get("status_http")
    fonte.ultimo_content_type = payload.get("content_type", "")
    fonte.ultimo_tamanho_bytes = payload.get("tamanho_bytes")
    fonte.ultimo_etag = payload.get("etag", "")
    fonte.ultimo_last_modified = payload.get("last_modified", "")
    fonte.verificada_em = agora
    fonte.ultimo_erro = ""
    if mudou:
        fonte.alterada_em = agora
    fonte.save(
        update_fields=[
            "ultimo_hash",
            "ultimo_status_http",
            "ultimo_content_type",
            "ultimo_tamanho_bytes",
            "ultimo_etag",
            "ultimo_last_modified",
            "verificada_em",
            "ultimo_erro",
            "alterada_em",
            "atualizado_em",
        ]
    )

    evento = None
    if mudou:
        evento = _criar_evento_mudanca(fonte, hash_anterior, hash_novo, payload)
        if evento:
            afetados = _marcar_itens_da_fonte_para_revalidacao(fonte, evento)
        else:
            afetados = {"tabelas_afetadas": 0, "extras_afetados": 0}
    else:
        afetados = {"tabelas_afetadas": 0, "extras_afetados": 0}

    return {
        "fonte_id": fonte.pk,
        "uf": fonte.uf,
        "status": "alterada" if mudou else "sem_mudanca",
        "evento_id": evento.pk if evento else None,
        "hash": hash_novo,
        **afetados,
    }


def monitorar_fontes_cartorio(uf=None, fonte_id=None, session=None):
    fontes = CartorioFonteMonitorada.objects.filter(ativa=True)
    if uf:
        fontes = fontes.filter(uf=str(uf).upper())
    if fonte_id:
        fontes = fontes.filter(pk=fonte_id)

    resultados = []
    resumo = {
        "fontes": 0,
        "alteradas": 0,
        "sem_mudanca": 0,
        "erros": 0,
        "eventos": 0,
        "resultados": resultados,
    }
    for fonte in fontes.order_by("uf", "nome"):
        resultado = verificar_fonte_cartorio(fonte, session=session)
        resultados.append(resultado)
        resumo["fontes"] += 1
        if resultado["status"] == "alterada":
            resumo["alteradas"] += 1
        elif resultado["status"] == "erro":
            resumo["erros"] += 1
        else:
            resumo["sem_mudanca"] += 1
        if resultado.get("evento_id"):
            resumo["eventos"] += 1

    logger.info("Monitoramento de fontes cartorarias concluido: %s", resumo)
    return resumo
