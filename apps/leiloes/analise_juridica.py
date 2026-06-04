import json
import logging
from io import BytesIO

import requests
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


class AnaliseJuridicaErro(Exception):
    """Erro operacional esperado na etapa de analise juridica."""


ANALISE_JURIDICA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resumo_executivo": {"type": "string"},
        "nivel_risco": {
            "type": "string",
            "enum": ["baixo", "medio", "alto", "critico", "indeterminado"],
        },
        "score_risco": {"type": "integer", "minimum": 0, "maximum": 100},
        "principais_alertas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "titulo": {"type": "string"},
                    "gravidade": {
                        "type": "string",
                        "enum": ["baixa", "media", "alta", "critica", "indeterminada"],
                    },
                    "evidencia": {"type": "string"},
                    "fonte": {"type": "string"},
                    "recomendacao": {"type": "string"},
                },
                "required": ["titulo", "gravidade", "evidencia", "fonte", "recomendacao"],
            },
        },
        "ocupacao": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "situacao": {"type": "string"},
                "evidencia": {"type": "string"},
                "recomendacao": {"type": "string"},
            },
            "required": ["situacao", "evidencia", "recomendacao"],
        },
        "onus_restricoes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "tipo": {"type": "string"},
                    "gravidade": {
                        "type": "string",
                        "enum": ["baixa", "media", "alta", "critica", "indeterminada"],
                    },
                    "evidencia": {"type": "string"},
                    "fonte": {"type": "string"},
                    "impacto": {"type": "string"},
                },
                "required": ["tipo", "gravidade", "evidencia", "fonte", "impacto"],
            },
        },
        "debitos_responsabilidades": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "tipo": {"type": "string"},
                    "responsavel": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "fonte": {"type": "string"},
                    "impacto": {"type": "string"},
                },
                "required": ["tipo", "responsavel", "evidencia", "fonte", "impacto"],
            },
        },
        "processos_mencionados": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "identificador": {"type": "string"},
                    "parte": {"type": "string"},
                    "risco": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "fonte": {"type": "string"},
                },
                "required": ["identificador", "parte", "risco", "evidencia", "fonte"],
            },
        },
        "cadeia_titularidade": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "resumo": {"type": "string"},
                "pontos_atencao": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["resumo", "pontos_atencao"],
        },
        "pontos_a_validar": {"type": "array", "items": {"type": "string"}},
        "limites_da_analise": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "resumo_executivo",
        "nivel_risco",
        "score_risco",
        "principais_alertas",
        "ocupacao",
        "onus_restricoes",
        "debitos_responsabilidades",
        "processos_mencionados",
        "cadeia_titularidade",
        "pontos_a_validar",
        "limites_da_analise",
    ],
}


def _agora_payload():
    agora = timezone.now()
    return {
        "gerado_em": agora.isoformat(),
        "gerado_em_display": timezone.localtime(agora).strftime("%d/%m/%Y %H:%M"),
    }


def _payload_status(status, mensagem, fontes=None, erro=""):
    return {
        "status": status,
        "mensagem": mensagem,
        "erro": erro,
        "modelo": getattr(settings, "OPENAI_LEGAL_ANALYSIS_MODEL", ""),
        "fontes": fontes or [],
        "resultado": None,
        **_agora_payload(),
    }


def _documentos_do_imovel(imovel):
    documentos = []
    if imovel.matricula_url:
        documentos.append(("Matricula", imovel.matricula_url))
    if imovel.edital_url:
        documentos.append(("Edital", imovel.edital_url))
    return documentos


def _headers_documento(imovel):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
        "Referer": imovel.link_caixa or "https://venda-imoveis.caixa.gov.br/sistema/index.asp",
    }


def _baixar_documento(url, imovel):
    limite_bytes = max(1, settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB) * 1024 * 1024
    try:
        resposta = requests.get(
            url,
            headers=_headers_documento(imovel),
            timeout=(10, 60),
            stream=True,
        )
        resposta.raise_for_status()
    except requests.RequestException as exc:
        raise AnaliseJuridicaErro(f"Falha ao baixar documento: {exc}") from exc

    conteudo = bytearray()
    for chunk in resposta.iter_content(chunk_size=65536):
        if not chunk:
            continue
        conteudo.extend(chunk)
        if len(conteudo) > limite_bytes:
            raise AnaliseJuridicaErro(
                f"Documento excedeu o limite de {settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB} MB"
            )

    if not conteudo:
        raise AnaliseJuridicaErro("Documento baixado sem conteudo")

    return bytes(conteudo), resposta.headers.get("content-type", "")


def _texto_util(texto):
    return " ".join((texto or "").split())


def _pagina_precisa_ocr(texto):
    return len(_texto_util(texto)) < settings.OPENAI_LEGAL_ANALYSIS_OCR_MIN_PAGE_CHARS


def _extrair_texto_ocr_pdf(conteudo, paginas_para_ocr):
    if not settings.OPENAI_LEGAL_ANALYSIS_OCR_ENABLED or not paginas_para_ocr:
        return {}, []

    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        return {}, [f"OCR indisponivel: {exc}"]

    textos_ocr = {}
    erros = []
    dpi = max(120, settings.OPENAI_LEGAL_ANALYSIS_OCR_DPI)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    try:
        documento = fitz.open(stream=conteudo, filetype="pdf")
    except Exception as exc:
        return {}, [f"OCR nao conseguiu abrir PDF: {exc}"]

    try:
        for numero_pagina in paginas_para_ocr:
            try:
                pagina = documento.load_page(numero_pagina - 1)
                pixmap = pagina.get_pixmap(matrix=matrix, alpha=False)
                imagem = Image.open(BytesIO(pixmap.tobytes("png")))
                texto = pytesseract.image_to_string(
                    imagem,
                    lang=settings.OPENAI_LEGAL_ANALYSIS_OCR_LANG,
                    config="--psm 6",
                    timeout=settings.OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS,
                )
                texto = texto.strip()
                if texto:
                    textos_ocr[numero_pagina] = texto
            except Exception as exc:
                erros.append(f"Pagina {numero_pagina}: {exc}")
    finally:
        documento.close()

    return textos_ocr, erros


def _extrair_texto_pdf(conteudo):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise AnaliseJuridicaErro("Pacote pypdf nao instalado") from exc

    try:
        leitor = PdfReader(BytesIO(conteudo))
        if leitor.is_encrypted:
            try:
                leitor.decrypt("")
            except Exception:
                pass
        paginas = list(leitor.pages)
    except Exception as exc:
        raise AnaliseJuridicaErro(f"Nao foi possivel abrir o PDF: {exc}") from exc

    textos_por_pagina = {}
    paginas_para_ocr = []
    max_paginas_ocr = max(0, settings.OPENAI_LEGAL_ANALYSIS_OCR_MAX_PAGES)

    for indice, pagina in enumerate(paginas, start=1):
        try:
            texto = pagina.extract_text() or ""
        except Exception as exc:
            logger.info("Falha ao extrair texto da pagina %s: %s", indice, exc)
            texto = ""
        texto = texto.strip()
        if texto:
            textos_por_pagina[indice] = texto
        if (
            settings.OPENAI_LEGAL_ANALYSIS_OCR_ENABLED
            and max_paginas_ocr
            and _pagina_precisa_ocr(texto)
            and len(paginas_para_ocr) < max_paginas_ocr
        ):
            paginas_para_ocr.append(indice)

    textos_ocr, erros_ocr = _extrair_texto_ocr_pdf(conteudo, paginas_para_ocr)
    for indice, texto_ocr in textos_ocr.items():
        texto_nativo = textos_por_pagina.get(indice, "")
        if _pagina_precisa_ocr(texto_nativo) or len(texto_ocr) > len(texto_nativo) * 2:
            textos_por_pagina[indice] = f"[OCR]\n{texto_ocr}"
        elif texto_ocr and texto_ocr not in texto_nativo:
            textos_por_pagina[indice] = f"{texto_nativo}\n\n[OCR complementar]\n{texto_ocr}"

    trechos = [
        f"[Pagina {indice}]\n{textos_por_pagina[indice]}"
        for indice in sorted(textos_por_pagina)
        if textos_por_pagina[indice].strip()
    ]
    metadata = {
        "paginas_ocr_tentadas": len(paginas_para_ocr),
        "paginas_ocr": len(textos_ocr),
        "ocr_erros": erros_ocr[:10],
        "metodo_extracao": "nativo+ocr" if textos_ocr else "nativo",
        "ocr_habilitado": settings.OPENAI_LEGAL_ANALYSIS_OCR_ENABLED,
    }

    return "\n\n".join(trechos).strip(), len(paginas), metadata


def _erro_texto_ausente(metadata):
    if metadata.get("ocr_habilitado"):
        if metadata.get("paginas_ocr_tentadas"):
            return "PDF sem texto extraivel mesmo apos OCR; pode ter baixa qualidade ou protecao"
        return "PDF sem texto extraivel"
    return "PDF sem texto extraivel; OCR esta desabilitado"


def _coletar_fontes(imovel):
    fontes = []
    for nome, url in _documentos_do_imovel(imovel):
        fonte = {
            "nome": nome,
            "url": url,
            "texto": "",
            "paginas": 0,
            "tamanho_bytes": 0,
            "erro": "",
            "paginas_ocr": 0,
            "paginas_ocr_tentadas": 0,
            "metodo_extracao": "",
            "ocr_erros": [],
        }
        try:
            conteudo, content_type = _baixar_documento(url, imovel)
            fonte["tamanho_bytes"] = len(conteudo)
            fonte["content_type"] = content_type
            texto, paginas, metadata = _extrair_texto_pdf(conteudo)
            fonte["texto"] = texto
            fonte["paginas"] = paginas
            fonte["paginas_ocr"] = metadata.get("paginas_ocr", 0)
            fonte["paginas_ocr_tentadas"] = metadata.get("paginas_ocr_tentadas", 0)
            fonte["metodo_extracao"] = metadata.get("metodo_extracao", "")
            fonte["ocr_erros"] = metadata.get("ocr_erros", [])
            if not texto:
                fonte["erro"] = _erro_texto_ausente(metadata)
        except AnaliseJuridicaErro as exc:
            fonte["erro"] = str(exc)
        fontes.append(fonte)
    return fontes


def _fontes_metadata(fontes):
    return [
        {
            "nome": fonte["nome"],
            "url": fonte["url"],
            "paginas": fonte.get("paginas", 0),
            "chars_extraidos": len(fonte.get("texto") or ""),
            "tamanho_bytes": fonte.get("tamanho_bytes", 0),
            "erro": fonte.get("erro", ""),
            "paginas_ocr": fonte.get("paginas_ocr", 0),
            "paginas_ocr_tentadas": fonte.get("paginas_ocr_tentadas", 0),
            "metodo_extracao": fonte.get("metodo_extracao", ""),
            "ocr_erros": fonte.get("ocr_erros", []),
        }
        for fonte in fontes
    ]


def _dados_imovel(imovel):
    return {
        "id_caixa": imovel.imovel_id_caixa,
        "endereco": imovel.endereco,
        "bairro": imovel.bairro or "",
        "cidade": imovel.cidade,
        "estado": imovel.estado,
        "cep": imovel.cep or "",
        "tipo": imovel.get_tipo_display(),
        "modalidade": imovel.modalidade_venda or "",
        "valor_avaliacao": str(imovel.valor_avaliacao or ""),
        "valor_minimo_lance": str(imovel.valor_minimo_lance or ""),
        "percentual_desconto": str(imovel.percentual_desconto or ""),
        "data_leilao": imovel.data_leilao.isoformat() if imovel.data_leilao else "",
        "ocupado_sinalizado": bool(imovel.ocupado),
        "aceita_financiamento": imovel.pode_financiar,
        "aceita_fgts": imovel.pode_fgts,
        "aceita_consorcio": imovel.pode_consorcio,
        "pendencias_sistema": imovel.pendencias or [],
        "descricao": imovel.descricao or "",
    }


def _montar_contexto_documentos(fontes):
    limite_total = max(10000, settings.OPENAI_LEGAL_ANALYSIS_TEXT_LIMIT)
    restante = limite_total
    blocos = []

    for fonte in fontes:
        texto = (fonte.get("texto") or "").strip()
        if not texto:
            continue

        if len(texto) > restante:
            texto = texto[:restante] + "\n[TEXTO TRUNCADO PELO LIMITE OPERACIONAL]"

        blocos.append(
            f"## Fonte: {fonte['nome']}\n"
            f"URL: {fonte['url']}\n"
            f"Paginas extraidas: {fonte.get('paginas') or 0}\n\n"
            f"{texto}"
        )
        restante -= len(texto)
        if restante <= 0:
            break

    return "\n\n---\n\n".join(blocos)


def _prompt_usuario(imovel, fontes):
    fontes_com_erro = [
        {
            "nome": fonte["nome"],
            "url": fonte["url"],
            "erro": fonte["erro"],
        }
        for fonte in fontes
        if fonte.get("erro")
    ]
    return (
        "Analise os documentos abaixo e produza uma triagem juridica estruturada "
        "para um usuario que avalia arrematar o imovel.\n\n"
        "Regras de evidencia:\n"
        "- Cite a fonte e o trecho/indicador que sustenta cada alerta.\n"
        "- Quando nao houver evidencia suficiente, marque como indeterminado.\n"
        "- Nao afirme ausencia de risco apenas por nao encontrar um termo.\n"
        "- Nao invente CPF, processo, credor, data, onus ou responsabilidade.\n"
        "- A resposta e triagem informativa, nao parecer juridico.\n\n"
        "Dados do imovel:\n"
        f"{json.dumps(_dados_imovel(imovel), ensure_ascii=False)}\n\n"
        "Documentos com erro ou texto ausente:\n"
        f"{json.dumps(fontes_com_erro, ensure_ascii=False)}\n\n"
        "Texto extraido dos documentos:\n"
        f"{_montar_contexto_documentos(fontes)}"
    )


def _extrair_texto_resposta(response):
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    partes = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            texto = getattr(content, "text", None)
            if texto:
                partes.append(texto)
    return "\n".join(partes).strip()


def _gerar_com_openai(imovel, fontes):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AnaliseJuridicaErro("Pacote openai nao instalado") from exc

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=settings.OPENAI_LEGAL_ANALYSIS_MODEL,
        reasoning={"effort": settings.OPENAI_LEGAL_ANALYSIS_REASONING_EFFORT},
        max_output_tokens=settings.OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS,
        text={
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "analise_juridica_leilao_caixa",
                "strict": True,
                "schema": ANALISE_JURIDICA_SCHEMA,
            },
        },
        input=[
            {
                "role": "system",
                "content": (
                    "Voce e um especialista brasileiro em leiloes de imoveis, "
                    "execucao judicial/extrajudicial, matricula imobiliaria e "
                    "edital da Caixa. Seu papel e identificar riscos provaveis, "
                    "lacunas de validacao e responsabilidades do arrematante com "
                    "base somente nas evidencias fornecidas."
                ),
            },
            {
                "role": "user",
                "content": _prompt_usuario(imovel, fontes),
            },
        ],
    )
    texto = _extrair_texto_resposta(response)
    if not texto:
        raise AnaliseJuridicaErro("A IA nao retornou texto estruturado")

    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise AnaliseJuridicaErro("A IA retornou JSON invalido") from exc


def analisar_imovel_caixa(imovel):
    if not settings.OPENAI_API_KEY:
        return _payload_status(
            "sem_api_key",
            "Configure OPENAI_API_KEY para gerar a analise juridica IA.",
        )

    if not _documentos_do_imovel(imovel):
        return _payload_status(
            "sem_documentos",
            "Este imovel ainda nao tem link de matricula ou edital para analise.",
        )

    fontes = _coletar_fontes(imovel)
    fontes_metadata = _fontes_metadata(fontes)
    if not any((fonte.get("texto") or "").strip() for fonte in fontes):
        return _payload_status(
            "sem_texto",
            "Nao foi possivel extrair texto util dos documentos disponiveis, mesmo com OCR.",
            fontes=fontes_metadata,
        )

    try:
        resultado = _gerar_com_openai(imovel, fontes)
    except AnaliseJuridicaErro as exc:
        logger.warning(
            "Analise juridica IA falhou para imovel %s: %s",
            imovel.imovel_id_caixa,
            exc,
        )
        return _payload_status(
            "erro",
            "Nao foi possivel concluir a analise juridica IA.",
            fontes=fontes_metadata,
            erro=str(exc)[:500],
        )
    except Exception as exc:
        logger.exception(
            "Erro inesperado na analise juridica IA do imovel %s",
            imovel.imovel_id_caixa,
        )
        return _payload_status(
            "erro",
            "Nao foi possivel concluir a analise juridica IA.",
            fontes=fontes_metadata,
            erro=str(exc)[:500],
        )

    return {
        "status": "concluida",
        "mensagem": "Analise juridica IA concluida.",
        "erro": "",
        "modelo": settings.OPENAI_LEGAL_ANALYSIS_MODEL,
        "fontes": fontes_metadata,
        "resultado": resultado,
        **_agora_payload(),
    }
