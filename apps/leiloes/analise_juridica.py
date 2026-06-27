import json
import logging
import unicodedata
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
                    "efeito_na_arrematacao": {
                        "type": "string",
                        "enum": [
                            "extinto_com_arrematacao",
                            "permanece_para_arrematante",
                            "indeterminado",
                        ],
                    },
                },
                "required": [
                    "tipo",
                    "gravidade",
                    "evidencia",
                    "fonte",
                    "impacto",
                    "efeito_na_arrematacao",
                ],
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
                    "valor_estimado": {"type": "string"},
                    "momento": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "fonte": {"type": "string"},
                    "impacto": {"type": "string"},
                },
                "required": [
                    "tipo",
                    "responsavel",
                    "valor_estimado",
                    "momento",
                    "evidencia",
                    "fonte",
                    "impacto",
                ],
            },
        },
        "inconsistencias": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "descricao": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "gravidade": {
                        "type": "string",
                        "enum": ["baixa", "media", "alta", "critica", "indeterminada"],
                    },
                },
                "required": ["descricao", "evidencia", "gravidade"],
            },
        },
        "checklist_due_diligence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "acao": {"type": "string"},
                    "prioridade": {
                        "type": "string",
                        "enum": ["alta", "media", "baixa"],
                    },
                    "motivo": {"type": "string"},
                },
                "required": ["acao", "prioridade", "motivo"],
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
        "inconsistencias",
        "checklist_due_diligence",
        "processos_mencionados",
        "cadeia_titularidade",
        "pontos_a_validar",
        "limites_da_analise",
    ],
}

AI_PROVIDERS_SUPORTADOS = {"openai", "anthropic", "gemini"}

MARCADORES_AUTENTICACAO = [
    "pedido de certidao",
    "certidao",
    "autenticidade",
    "validacao",
    "validar o documento",
    "selo de autenticidade",
    "assinador",
    "codigo de validacao",
]

MARCADORES_REGISTRAIS = [
    "matricula",
    "r-",
    "av-",
    "alienacao fiduciaria",
    "consolidacao",
    "proprietario",
    "credor",
    "devedor",
    "onus",
    "penhora",
    "indisponibilidade",
    "averbacao",
]


def _setting_str(nome, default=""):
    return str(getattr(settings, nome, default) or "").strip()


def _provider_ia():
    provider = _setting_str("AI_LEGAL_ANALYSIS_PROVIDER", "openai").lower()
    aliases = {
        "open_ai": "openai",
        "claude": "anthropic",
        "anthropic_claude": "anthropic",
        "google": "gemini",
        "google_gemini": "gemini",
    }
    return aliases.get(provider, provider)


def _modelo_ia():
    return _setting_str(
        "AI_LEGAL_ANALYSIS_MODEL",
        _setting_str("OPENAI_LEGAL_ANALYSIS_MODEL", "gpt-5.5"),
    )


# Esforço de raciocínio agnóstico de provedor. O nível normalizado é traduzido
# para o formato de cada provedor: "effort" no OpenAI e orçamento de tokens de
# pensamento (thinkingBudget) no Gemini. No Anthropic, o pensamento estendido é
# incompatível com saída estruturada via tool_choice forçado, então a análise
# Anthropic não usa thinking (ver _gerar_com_anthropic).
# Níveis válidos para reasoning.effort no gpt-5.5: none/low/medium/high/xhigh.
# ("minimal" era do gpt-5 e foi renomeado para "none".)
_GEMINI_THINKING_BUDGET = {
    "none": 0,
    "low": 1024,
    "medium": 4096,
    "high": 12000,
    "xhigh": 24576,
}


def _nivel_esforco_normalizado(nivel):
    nivel = (nivel or "").strip().lower()
    if nivel in {"none", "minimal", "minimo", "mínimo", "nenhum"}:
        return "none"
    if nivel in {"low", "baixo"}:
        return "low"
    if nivel in {"xhigh", "max", "maximo", "máximo"}:
        return "xhigh"
    if nivel in {"high", "alto"}:
        return "high"
    if nivel in {"medium", "medio", "médio"}:
        return "medium"
    return "medium"


def _esforco_ia():
    return _nivel_esforco_normalizado(
        _setting_str("AI_LEGAL_ANALYSIS_REASONING_EFFORT", "high")
    )


def _reasoning_openai_param(nivel):
    return {"effort": _nivel_esforco_normalizado(nivel)}


def _gemini_thinking_config(nivel):
    return {"thinkingBudget": _GEMINI_THINKING_BUDGET[_nivel_esforco_normalizado(nivel)]}


def _api_key_ia(provider):
    chave_generica = _setting_str("AI_LEGAL_ANALYSIS_API_KEY")
    if chave_generica:
        return chave_generica

    if provider == "openai":
        return _setting_str("OPENAI_API_KEY")
    if provider == "anthropic":
        return _setting_str("ANTHROPIC_API_KEY")
    if provider == "gemini":
        return _setting_str("GEMINI_API_KEY", _setting_str("GOOGLE_API_KEY"))
    return ""


def _nome_variavel_chave(provider):
    return {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider, "AI_LEGAL_ANALYSIS_API_KEY")


def _system_prompt_ia():
    return (
        "Voce e um especialista brasileiro em leiloes de imoveis, "
        "execucao judicial/extrajudicial, matricula imobiliaria e "
        "edital da Caixa. Seu papel e identificar riscos provaveis, "
        "lacunas de validacao e responsabilidades do arrematante com "
        "base somente nas evidencias fornecidas. Voce classifica cada onus "
        "ou restricao quanto ao seu efeito na arrematacao (se e extinto com a "
        "arrematacao ou se permanece para o arrematante), aponta inconsistencias "
        "entre os dados do sistema/anuncio e o teor dos documentos, e propoe um "
        "checklist de due diligence priorizado e acionavel."
    )


REGRAS_ENRIQUECIMENTO = (
    "- Considere TODOS os documentos fornecidos (matricula, edital, peticoes/processos, "
    "certidoes e anexos), nao apenas matricula e edital.\n"
    "- Para cada onus/restricao, classifique o efeito na arrematacao: "
    "'extinto_com_arrematacao' (ex.: penhoras e a propria hipoteca/alienacao fiduciaria "
    "que originou a execucao costumam ser extintas), 'permanece_para_arrematante' "
    "(ex.: tributos propter rem, servidoes, usufruto, locacao com clausula de vigencia, "
    "restricoes urbanisticas) ou 'indeterminado' quando faltar base. Fundamente na "
    "natureza do ato e nas condicoes do edital; nao chute.\n"
    "- Em debitos_responsabilidades, quando o documento trouxer valores, preencha "
    "valor_estimado e o momento em que sao devidos (ex.: 'ate a data da arrematacao', "
    "'apos a imissao na posse'); senao use string vazia.\n"
    "- Liste inconsistencias entre os dados do sistema/anuncio e o que os documentos "
    "mostram (ex.: imovel sinalizado como desocupado mas a matricula/edital indica "
    "ocupacao, usufruto ou acao possessoria; divergencia de area, titularidade ou "
    "metragem). So aponte com evidencia concreta.\n"
    "- Monte um checklist_due_diligence priorizado (alta/media/baixa) com acoes "
    "praticas e o motivo de cada uma (ex.: obter certidao de onus atualizada, verificar "
    "debitos de IPTU/condominio, confirmar situacao de ocupacao, conferir transito em "
    "julgado do processo).\n"
)


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
        "provider": _provider_ia(),
        "modelo": _modelo_ia(),
        "fontes": fontes or [],
        "resultado": None,
        **_agora_payload(),
    }


def _documentos_do_imovel(imovel):
    """Retorna lista de (nome, url) para ImovelCaixa ou Imovel avulso."""
    documentos = []
    # ImovelCaixa: campos diretos
    if hasattr(imovel, "matricula_url") and imovel.matricula_url:
        documentos.append(("Matricula", imovel.matricula_url))
    if hasattr(imovel, "edital_url") and imovel.edital_url:
        documentos.append(("Edital", imovel.edital_url))
    return documentos


def _documentos_do_imovel_avulso(imovel, arquivos_imovel=None):
    """Retorna lista de (nome, storage_field_ou_url, tipo) para Imovel avulso.

    Prioriza arquivos enviados (compatível com S3/local) sobre URLs externas.
    tipo == 'storage' → FieldFile do Django (lido via .open())
    tipo == 'url'     → URL externa (baixada via requests)
    """
    documentos = []

    if arquivos_imovel:
        for arq in arquivos_imovel:
            if arq.categoria in ("matricula", "edital") and arq.arquivo:
                nome = arq.categoria.capitalize()
                documentos.append((nome, arq.arquivo, "storage"))

    # Complementa com URLs externas se a categoria ainda não foi coberta por arquivo
    categorias_cobertas = {d[0].lower() for d in documentos}
    matricula_url = getattr(imovel, "matricula_url_avulso", None) or ""
    edital_url = getattr(imovel, "edital_url_avulso", None) or ""

    if matricula_url and "matricula" not in categorias_cobertas:
        documentos.append(("Matricula", matricula_url, "url"))
    if edital_url and "edital" not in categorias_cobertas:
        documentos.append(("Edital", edital_url, "url"))

    return documentos


def _headers_documento(imovel=None):
    referer = "https://venda-imoveis.caixa.gov.br/sistema/index.asp"
    if imovel and hasattr(imovel, "link_caixa") and imovel.link_caixa:
        referer = imovel.link_caixa
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
        "Referer": referer,
    }


def _ler_arquivo_storage(field_file):
    """Lê um PDF via Django storage (local ou S3) e retorna os bytes.

    Fallback: se o storage local falhar (ex.: Celery sem env vars de S3 configuradas),
    tenta baixar via URL pública do arquivo (funciona quando o bucket é público).
    """
    import requests as _requests

    limite_bytes = max(1, settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB) * 1024 * 1024
    conteudo = None

    # Tentativa 1: Django storage (funciona para local e S3 quando configurado)
    try:
        with field_file.open("rb") as f:
            conteudo = f.read(limite_bytes + 1)
    except Exception as exc_storage:
        # Tentativa 2: URL pública do arquivo (funciona quando bucket B2/S3 é público
        # ou quando o worker não tem as variáveis de storage configuradas)
        try:
            url = field_file.url
        except Exception:
            raise AnaliseJuridicaErro(f"Falha ao ler arquivo do storage: {exc_storage}") from exc_storage

        if not url or url.startswith("/"):
            raise AnaliseJuridicaErro(f"Falha ao ler arquivo do storage: {exc_storage}") from exc_storage

        try:
            resp = _requests.get(url, timeout=30)
            resp.raise_for_status()
            conteudo = resp.content[: limite_bytes + 1]
        except Exception as exc_url:
            raise AnaliseJuridicaErro(
                f"Falha ao ler arquivo do storage: {exc_storage}; e via URL: {exc_url}"
            ) from exc_url

    if len(conteudo) > limite_bytes:
        raise AnaliseJuridicaErro(
            f"Arquivo excede o limite de {settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB} MB"
        )
    if not _conteudo_parece_pdf(conteudo):
        raise AnaliseJuridicaErro("Arquivo no storage não parece um PDF válido")
    return conteudo, "application/pdf"


def _baixar_documento(url, imovel=None):
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

    conteudo_bytes = bytes(conteudo)
    content_type = resposta.headers.get("content-type", "")
    if not _conteudo_parece_pdf(conteudo_bytes, content_type):
        raise AnaliseJuridicaErro(_erro_documento_nao_pdf(conteudo_bytes, content_type))

    return conteudo_bytes, content_type


def _conteudo_parece_pdf(conteudo, content_type=""):
    cabecalho = (conteudo or b"").lstrip()[:500]
    cabecalho_lower = cabecalho.lower()
    if b"radware bot manager captcha" in cabecalho_lower or b"captcha" in cabecalho_lower:
        return False
    if cabecalho_lower.startswith((b"<html", b"<head", b"<!doctype html")):
        return False
    # O magic byte do PDF é maiúsculo (%PDF) — comparar no buffer original,
    # não no lower(), senão "%pdf" nunca casa e PDFs válidos são rejeitados.
    if cabecalho.startswith(b"%PDF"):
        return True
    return "application/pdf" in (content_type or "").lower()


def _erro_documento_nao_pdf(conteudo, content_type=""):
    amostra = (conteudo or b"")[:500].lower()
    if b"radware bot manager captcha" in amostra or b"captcha" in amostra:
        return "A Caixa retornou HTML/CAPTCHA no lugar do PDF do documento"
    if b"<html" in amostra or b"<head" in amostra or b"<!doctype html" in amostra:
        return f"A Caixa retornou HTML no lugar do PDF do documento (content-type: {content_type or 'desconhecido'})"
    return f"Documento baixado nao parece PDF valido (content-type: {content_type or 'desconhecido'})"


def _texto_util(texto):
    return " ".join((texto or "").split())


def _texto_normalizado(texto):
    texto_sem_acento = (
        unicodedata.normalize("NFKD", texto or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return _texto_util(texto_sem_acento).lower()


def _contar_marcadores(texto, marcadores):
    texto_normalizado = _texto_normalizado(texto)
    return sum(texto_normalizado.count(marcador) for marcador in marcadores)


def _texto_parece_apenas_autenticacao(texto):
    texto_limpo = _texto_normalizado(texto)
    if not texto_limpo:
        return False

    autenticacao = _contar_marcadores(texto_limpo, MARCADORES_AUTENTICACAO)
    registrais = _contar_marcadores(texto_limpo, MARCADORES_REGISTRAIS)
    tem_validacao = "validar" in texto_limpo or "autenticidade" in texto_limpo
    tem_pedido_certidao = "pedido de certidao" in texto_limpo

    return (
        autenticacao >= 2
        and tem_validacao
        and (registrais <= 2 or tem_pedido_certidao)
    )


def _pagina_precisa_ocr(texto):
    texto_limpo = _texto_util(texto)
    if len(texto_limpo) < settings.OPENAI_LEGAL_ANALYSIS_OCR_MIN_PAGE_CHARS:
        return True
    return _texto_parece_apenas_autenticacao(texto_limpo)


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


def _imagens_por_pagina(conteudo):
    """Conta imagens por página (1-indexed) via fitz. {} se indisponível.

    Usado para detectar páginas escaneadas (matrícula/edital em imagem com um
    cabeçalho fino de validação por cima), que passariam batido no gatilho de OCR
    baseado só no tamanho do texto.
    """
    try:
        import fitz
    except ImportError:
        return {}
    try:
        documento = fitz.open(stream=conteudo, filetype="pdf")
    except Exception:
        return {}
    contagem = {}
    try:
        for indice in range(documento.page_count):
            try:
                contagem[indice + 1] = len(documento.load_page(indice).get_images())
            except Exception:
                contagem[indice + 1] = 0
    finally:
        documento.close()
    return contagem


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
    imagens_por_pagina = _imagens_por_pagina(conteudo)
    limiar_escaneada = max(0, getattr(settings, "OPENAI_LEGAL_ANALYSIS_OCR_SCANNED_TEXT_LIMIT", 1500))

    for indice, pagina in enumerate(paginas, start=1):
        try:
            texto = pagina.extract_text() or ""
        except Exception as exc:
            logger.info("Falha ao extrair texto da pagina %s: %s", indice, exc)
            texto = ""
        texto = texto.strip()
        if texto:
            textos_por_pagina[indice] = texto

        precisa_ocr = _pagina_precisa_ocr(texto)
        # Página escaneada: tem imagem e pouco texto nativo (ex.: matrícula/edital
        # digitalizado com só o cabeçalho de validação extraível). O teor está na
        # imagem e precisa de OCR mesmo passando do mínimo de caracteres.
        if not precisa_ocr and limiar_escaneada and imagens_por_pagina.get(indice, 0) > 0:
            if len(_texto_util(texto)) < limiar_escaneada:
                precisa_ocr = True

        if (
            settings.OPENAI_LEGAL_ANALYSIS_OCR_ENABLED
            and max_paginas_ocr
            and precisa_ocr
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


def _fontes_de_cache(cache):
    """Converte o cache de Imovel.documentos_texto em fontes para a análise.

    Permite que a análise avulsa use TODOS os documentos anexados (matrícula,
    edital, processos, certidões e demais anexos, incluindo imagens via OCR),
    reaproveitando o texto já extraído pelo chat sem reprocessar OCR.
    """
    rotulo_categoria = {
        "matricula": "Matrícula",
        "edital": "Edital",
        "processo": "Processo judicial",
        "certidao": "Certidão",
        "financeiro": "Financeiro",
        "apoio": "Apoio",
        "outro": "Outro",
    }
    fontes = []
    for entrada in (cache or {}).values():
        categoria = entrada.get("categoria") or ""
        nome = entrada.get("nome") or rotulo_categoria.get(categoria, "Documento")
        fontes.append(
            {
                "nome": nome,
                "url": "",
                "arquivo": nome,
                "categoria": categoria,
                "texto": entrada.get("texto") or "",
                "paginas": entrada.get("paginas") or 0,
                "tamanho_bytes": 0,
                "erro": entrada.get("erro") or "",
                "paginas_ocr": 0,
                "paginas_ocr_tentadas": 0,
                "metodo_extracao": entrada.get("metodo") or "",
                "ocr_erros": [],
            }
        )
    return fontes


def _coletar_fontes_avulso(documentos):
    """Coleta fontes para imóvel avulso: lê via Django storage ou baixa de URL."""
    fontes = []
    for entrada in documentos:
        nome, origem, tipo = entrada
        # origem é FieldFile (storage) ou str (url)
        label_origem = getattr(origem, "name", None) or (origem if isinstance(origem, str) else "")
        fonte = {
            "nome": nome,
            "url": origem if tipo == "url" else "",
            "arquivo": label_origem if tipo == "storage" else "",
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
            if tipo == "storage":
                conteudo, content_type = _ler_arquivo_storage(origem)
            else:
                conteudo, content_type = _baixar_documento(origem)
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


def _limitar_texto(valor, limite=2500):
    texto = _texto_util(valor)
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + " [TRUNCADO]"


def _dados_caixa_estruturados(imovel):
    detalhe = ((imovel.detalhes or {}).get("detalhe_caixa") or {})
    if not detalhe:
        return {}

    campos = [
        "url",
        "titulo",
        "numero_imovel_formatado",
        "matriculas",
        "comarca",
        "oficio",
        "inscricao_imobiliaria",
        "averbacao_leiloes_negativos",
        "edital",
        "numero_item",
        "leiloeiro",
        "leiloeiro_site",
        "edital_publicado_em",
        "valor_avaliacao",
        "valor_minimo_lance",
        "tipo_imovel",
        "area_total",
        "area_privativa",
        "area_terreno",
        "datas_leilao",
    ]
    dados = {
        campo: detalhe.get(campo)
        for campo in campos
        if detalhe.get(campo) not in (None, "", [], {})
    }
    for campo in ["descricao", "formas_pagamento_texto", "regras_pagamento_texto"]:
        if detalhe.get(campo):
            dados[campo] = _limitar_texto(detalhe.get(campo), 2500)
    return dados


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

        origem = fonte.get("url") or fonte.get("arquivo") or ""
        blocos.append(
            f"## Fonte: {fonte['nome']}\n"
            f"Origem: {origem}\n"
            f"Paginas extraidas: {fonte.get('paginas') or 0}\n\n"
            f"{texto}"
        )
        restante -= len(texto)
        if restante <= 0:
            break

    return "\n\n---\n\n".join(blocos)


def _dados_imovel_avulso(imovel):
    return {
        "endereco": imovel.endereco,
        "cidade": imovel.cidade,
        "estado": imovel.estado,
        "tipo": imovel.get_tipo_imovel_display(),
        "tipo_leilao": imovel.tipo_leilao,
        "data_leilao": imovel.data_leilao.isoformat() if imovel.data_leilao else "",
        "valor_avaliacao": str(imovel.avaliacao or ""),
        "lance": str(imovel.lance or ""),
        "obs": _limitar_texto(imovel.obs or "", 1500),
    }


def _prompt_usuario_avulso(imovel, fontes):
    fontes_com_erro = [
        {
            "nome": fonte["nome"],
            "origem": fonte.get("url") or fonte.get("arquivo") or "",
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
        "- Nao use 'matricula atualizada' como alerta generico. So recomende atualizacao quando a data da certidao for antiga, quando a matricula trouxer apenas validacao/autenticacao ou quando faltar teor registral.\n"
        "- Quando houver atos registrais legiveis, extraia os atos concretos (R/AV), datas, partes, onus, consolidacao, penhoras e indisponibilidades antes de listar lacunas.\n"
        f"{REGRAS_ENRIQUECIMENTO}"
        "- A resposta e triagem informativa, nao parecer juridico.\n\n"
        "Dados do imovel:\n"
        f"{json.dumps(_dados_imovel_avulso(imovel), ensure_ascii=False)}\n\n"
        "Documentos com erro ou texto ausente:\n"
        f"{json.dumps(fontes_com_erro, ensure_ascii=False)}\n\n"
        "Texto extraido dos documentos:\n"
        f"{_montar_contexto_documentos(fontes)}"
    )


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
        "- Nao use 'matricula atualizada' como alerta generico. So recomende atualizacao quando a data da certidao for antiga, quando a matricula trouxer apenas validacao/autenticacao ou quando faltar teor registral.\n"
        "- Quando houver atos registrais legiveis, extraia os atos concretos (R/AV), datas, partes, onus, consolidacao, penhoras e indisponibilidades antes de listar lacunas.\n"
        "- Use os dados estruturados da pagina Caixa como fonte complementar para condicoes de venda, despesas e responsabilidades quando o edital PDF nao estiver extraivel.\n"
        f"{REGRAS_ENRIQUECIMENTO}"
        "- A resposta e triagem informativa, nao parecer juridico.\n\n"
        "Dados do imovel:\n"
        f"{json.dumps(_dados_imovel(imovel), ensure_ascii=False)}\n\n"
        "Dados estruturados extraidos da pagina da Caixa:\n"
        f"{json.dumps(_dados_caixa_estruturados(imovel), ensure_ascii=False)}\n\n"
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


def _json_de_texto(texto, mensagem_erro):
    texto = (texto or "").strip()
    if texto.startswith("```"):
        linhas = texto.splitlines()
        if linhas and linhas[0].startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].startswith("```"):
            linhas = linhas[:-1]
        texto = "\n".join(linhas).strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise AnaliseJuridicaErro(mensagem_erro) from exc


def _post_json(url, payload, headers=None, params=None):
    try:
        resposta = requests.post(
            url,
            headers=headers or {},
            params=params or {},
            json=payload,
            timeout=(10, 180),
        )
        resposta.raise_for_status()
    except requests.HTTPError as exc:
        corpo = ""
        if exc.response is not None:
            corpo = (exc.response.text or "")[:700]
        raise AnaliseJuridicaErro(f"Falha na API de IA: {corpo or exc}") from exc
    except requests.RequestException as exc:
        raise AnaliseJuridicaErro(f"Falha de comunicacao com a API de IA: {exc}") from exc

    try:
        return resposta.json()
    except ValueError as exc:
        raise AnaliseJuridicaErro("A API de IA retornou resposta sem JSON valido") from exc


def _schema_gemini(schema):
    tipo_map = {
        "object": "OBJECT",
        "array": "ARRAY",
        "string": "STRING",
        "integer": "INTEGER",
        "number": "NUMBER",
        "boolean": "BOOLEAN",
    }
    convertido = {}
    tipo = schema.get("type")
    if tipo:
        convertido["type"] = tipo_map.get(tipo, str(tipo).upper())
    if "description" in schema:
        convertido["description"] = schema["description"]
    if "enum" in schema:
        convertido["enum"] = schema["enum"]
    if "required" in schema:
        convertido["required"] = schema["required"]
    if "properties" in schema:
        convertido["properties"] = {
            nome: _schema_gemini(valor)
            for nome, valor in schema["properties"].items()
        }
    if "items" in schema:
        convertido["items"] = _schema_gemini(schema["items"])
    return convertido


def _gerar_com_openai(prompt_usuario, api_key, modelo, esforco):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AnaliseJuridicaErro("Pacote openai nao instalado") from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=modelo,
        reasoning=_reasoning_openai_param(esforco),
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
                "content": _system_prompt_ia(),
            },
            {
                "role": "user",
                "content": prompt_usuario,
            },
        ],
    )
    texto = _extrair_texto_resposta(response)
    if not texto:
        raise AnaliseJuridicaErro("A IA nao retornou texto estruturado")

    return _json_de_texto(texto, "A IA retornou JSON invalido")


def _gerar_com_anthropic(prompt_usuario, api_key, modelo, esforco=None):
    # O pensamento estendido do Claude exige tool_choice "auto" e temperature 1,
    # incompatível com a saída estruturada forçada usada aqui. Por isso o esforço
    # de raciocínio não é aplicado no caminho Anthropic da análise estruturada.
    payload = {
        "model": modelo,
        "max_tokens": settings.OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS,
        "temperature": 0,
        "system": _system_prompt_ia(),
        "messages": [
            {
                "role": "user",
                "content": prompt_usuario,
            }
        ],
        "tools": [
            {
                "name": "analise_juridica_leilao_caixa",
                "description": "Retorna uma analise juridica estruturada de imovel de leilao Caixa.",
                "input_schema": ANALISE_JURIDICA_SCHEMA,
            }
        ],
        "tool_choice": {
            "type": "tool",
            "name": "analise_juridica_leilao_caixa",
        },
    }
    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": _setting_str("ANTHROPIC_API_VERSION", "2023-06-01"),
        },
    )

    textos = []
    for item in data.get("content", []) or []:
        if item.get("type") == "tool_use" and item.get("name") == "analise_juridica_leilao_caixa":
            resultado = item.get("input")
            if isinstance(resultado, dict):
                return resultado
        if item.get("type") == "text" and item.get("text"):
            textos.append(item["text"])

    return _json_de_texto("\n".join(textos), "A IA retornou resposta Anthropic sem JSON valido")


def _gerar_com_gemini(prompt_usuario, api_key, modelo, esforco):
    model_path = modelo if modelo.startswith("models/") else f"models/{modelo}"
    payload = {
        "systemInstruction": {
            "parts": [{"text": _system_prompt_ia()}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt_usuario}],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": settings.OPENAI_LEGAL_ANALYSIS_MAX_OUTPUT_TOKENS,
            "responseMimeType": "application/json",
            "responseSchema": _schema_gemini(ANALISE_JURIDICA_SCHEMA),
            # thinkingConfig requer Gemini 2.5+; em modelos sem suporte, ajuste
            # AI_LEGAL_ANALYSIS_REASONING_EFFORT ou use outro provedor.
            "thinkingConfig": _gemini_thinking_config(esforco),
        },
    }
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent",
        payload,
        headers={"content-type": "application/json"},
        params={"key": api_key},
    )

    partes = (
        ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts")
        or []
    )
    texto = "\n".join(parte.get("text", "") for parte in partes if parte.get("text"))
    if not texto:
        raise AnaliseJuridicaErro("A IA nao retornou conteudo Gemini estruturado")
    return _json_de_texto(texto, "A IA retornou resposta Gemini sem JSON valido")


def _gerar_com_ia(prompt_usuario, provider, api_key, modelo, esforco=None):
    if not modelo:
        raise AnaliseJuridicaErro("Configure AI_LEGAL_ANALYSIS_MODEL com o modelo da IA.")
    if provider != "openai" and modelo.startswith("gpt-"):
        raise AnaliseJuridicaErro(
            "Configure AI_LEGAL_ANALYSIS_MODEL com um modelo compativel com o provider escolhido."
        )
    if esforco is None:
        esforco = _esforco_ia()
    if provider == "openai":
        return _gerar_com_openai(prompt_usuario, api_key, modelo, esforco)
    if provider == "anthropic":
        return _gerar_com_anthropic(prompt_usuario, api_key, modelo, esforco)
    if provider == "gemini":
        return _gerar_com_gemini(prompt_usuario, api_key, modelo, esforco)
    raise AnaliseJuridicaErro(f"Provider de IA nao suportado: {provider}")


def analisar_imovel_caixa(imovel):
    provider = _provider_ia()
    modelo = _modelo_ia()

    if provider not in AI_PROVIDERS_SUPORTADOS:
        return _payload_status(
            "erro_configuracao",
            "Provider de IA nao suportado. Use openai, anthropic ou gemini.",
            erro=f"AI_LEGAL_ANALYSIS_PROVIDER={provider}",
        )

    api_key = _api_key_ia(provider)
    if not api_key:
        return _payload_status(
            "sem_api_key",
            (
                "Configure AI_LEGAL_ANALYSIS_API_KEY ou "
                f"{_nome_variavel_chave(provider)} para gerar a analise juridica IA."
            ),
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
        resultado = _gerar_com_ia(_prompt_usuario(imovel, fontes), provider, api_key, modelo)
    except AnaliseJuridicaErro as exc:
        logger.warning(
            "Analise juridica IA falhou para imovel %s (%s/%s): %s",
            imovel.imovel_id_caixa,
            provider,
            modelo,
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
        "provider": provider,
        "modelo": modelo,
        "fontes": fontes_metadata,
        "resultado": resultado,
        **_agora_payload(),
    }


def analisar_imovel_avulso(imovel, arquivos_imovel=None):
    """Gera análise jurídica para imóvel avulso (não vinculado à Caixa).

    Aceita PDFs via upload (ImovelArquivo com categoria matricula/edital)
    ou URLs externas nos atributos matricula_url_avulso / edital_url_avulso.
    """
    provider = _provider_ia()
    modelo = _modelo_ia()

    if provider not in AI_PROVIDERS_SUPORTADOS:
        return _payload_status(
            "erro_configuracao",
            "Provider de IA nao suportado. Use openai, anthropic ou gemini.",
            erro=f"AI_LEGAL_ANALYSIS_PROVIDER={provider}",
        )

    api_key = _api_key_ia(provider)
    if not api_key:
        return _payload_status(
            "sem_api_key",
            (
                "Configure AI_LEGAL_ANALYSIS_API_KEY ou "
                f"{_nome_variavel_chave(provider)} para gerar a analise juridica IA."
            ),
        )

    # Usa TODOS os documentos anexados (matrícula, edital, processos, certidões
    # e demais anexos, incluindo imagens via OCR), reaproveitando o cache de texto.
    # Quando o imóvel é vinculado à Caixa, inclui também a matrícula/edital oficiais.
    try:
        from apps.imoveis.documentos_texto import garantir_textos_documentos

        imovel_caixa = None
        if getattr(imovel, "caixa_imovel_id", None):
            from .models import ImovelCaixa

            imovel_caixa = ImovelCaixa.objects.filter(
                imovel_id_caixa=imovel.caixa_imovel_id
            ).first()

        cache = garantir_textos_documentos(imovel, imovel_caixa)
        fontes = _fontes_de_cache(cache)
    except Exception:  # noqa: BLE001 - fallback para o coletor clássico
        logger.exception("Falha ao usar cache de documentos do imovel %s; usando coletor classico", imovel.pk)
        documentos = _documentos_do_imovel_avulso(imovel, arquivos_imovel)
        fontes = _coletar_fontes_avulso(documentos)

    if not fontes:
        return _payload_status(
            "sem_documentos",
            "Anexe a matrícula, o edital ou outros documentos ao imóvel para iniciar a análise.",
        )

    fontes_metadata = _fontes_metadata(fontes)
    if not any((fonte.get("texto") or "").strip() for fonte in fontes):
        return _payload_status(
            "sem_texto",
            "Nao foi possivel extrair texto util dos documentos enviados, mesmo com OCR.",
            fontes=fontes_metadata,
        )

    try:
        resultado = _gerar_com_ia(_prompt_usuario_avulso(imovel, fontes), provider, api_key, modelo)
    except AnaliseJuridicaErro as exc:
        logger.warning(
            "Analise juridica IA falhou para imovel avulso %s (%s/%s): %s",
            imovel.pk,
            provider,
            modelo,
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
            "Erro inesperado na analise juridica IA do imovel avulso %s",
            imovel.pk,
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
        "provider": provider,
        "modelo": modelo,
        "fontes": fontes_metadata,
        "resultado": resultado,
        **_agora_payload(),
    }
