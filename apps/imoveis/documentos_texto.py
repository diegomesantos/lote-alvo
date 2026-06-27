"""Extração e cache do texto dos documentos de um imóvel.

Reaproveita o pipeline de extração da análise jurídica (download, leitura via
storage, PDF + OCR) e adiciona OCR de imagens isoladas (foto de matrícula etc.).

O texto extraído é persistido em ``Imovel.documentos_texto`` (JSONField),
indexado por documento com um *fingerprint*, para não reprocessar OCR a cada
mensagem do chat. Documentos novos ou alterados são reprocessados sob demanda.
"""

import logging
from io import BytesIO

from django.conf import settings

from apps.leiloes.analise_juridica import (
    AnaliseJuridicaErro,
    _baixar_documento,
    _conteudo_parece_pdf,
    _extrair_texto_pdf,
)

logger = logging.getLogger(__name__)

# Incremente quando o pipeline de extração melhorar (ex.: novo gatilho de OCR).
# Entradas do cache com versão diferente são reprocessadas uma vez.
EXTRACAO_VERSION = 2

EXTENSOES_PDF = {".pdf"}
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif"}


def _limite_bytes():
    return max(1, settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB) * 1024 * 1024


def _extensao(nome):
    nome = (nome or "").lower()
    ponto = nome.rfind(".")
    return nome[ponto:] if ponto != -1 else ""


def _ler_bytes_storage(field_file):
    """Lê os bytes de um arquivo via Django storage com fallback para URL pública."""
    limite = _limite_bytes()
    try:
        with field_file.open("rb") as f:
            conteudo = f.read(limite + 1)
    except Exception as exc_storage:
        url = ""
        try:
            url = field_file.url
        except Exception:
            url = ""
        if not url or url.startswith("/"):
            raise AnaliseJuridicaErro(f"Falha ao ler arquivo: {exc_storage}") from exc_storage
        import requests

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            conteudo = resp.content[: limite + 1]
        except Exception as exc_url:
            raise AnaliseJuridicaErro(
                f"Falha ao ler arquivo: {exc_storage}; e via URL: {exc_url}"
            ) from exc_url

    if len(conteudo) > limite:
        raise AnaliseJuridicaErro(
            f"Arquivo excede o limite de {settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB} MB"
        )
    if not conteudo:
        raise AnaliseJuridicaErro("Arquivo vazio")
    return bytes(conteudo)


def _baixar_url_documento(url, imovel_caixa, permitir_playwright):
    """Baixa um documento por URL. Para URLs da Caixa que caem no anti-bot
    (Radware/CAPTCHA), faz fallback para download via navegador (Playwright)."""
    try:
        conteudo, _ = _baixar_documento(url, imovel_caixa)
        return conteudo
    except AnaliseJuridicaErro as exc:
        msg = str(exc).lower()
        bloqueio_antibot = "captcha" in msg or "html no lugar" in msg or "html/captcha" in msg
        if not (permitir_playwright and bloqueio_antibot):
            raise
        logger.info("Download direto bloqueado pelo anti-bot da Caixa; tentando via navegador: %s", url)

    from apps.leiloes.caixa_csv import baixar_documento_caixa_playwright

    referer = getattr(imovel_caixa, "link_caixa", None) if imovel_caixa else None
    try:
        conteudo = baixar_documento_caixa_playwright(url, referer_url=referer)
    except Exception as exc:  # noqa: BLE001
        raise AnaliseJuridicaErro(f"Falha ao baixar documento da Caixa via navegador: {exc}") from exc

    limite = _limite_bytes()
    if len(conteudo) > limite:
        raise AnaliseJuridicaErro(
            f"Documento excede o limite de {settings.OPENAI_LEGAL_ANALYSIS_DOWNLOAD_LIMIT_MB} MB"
        )
    if not _conteudo_parece_pdf(conteudo):
        raise AnaliseJuridicaErro("Documento da Caixa baixado via navegador não parece um PDF válido")
    return conteudo


def _ocr_imagem(conteudo):
    if not settings.OPENAI_LEGAL_ANALYSIS_OCR_ENABLED:
        raise AnaliseJuridicaErro("OCR desabilitado; imagem não pode ser lida")
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise AnaliseJuridicaErro(f"OCR indisponível: {exc}") from exc

    try:
        imagem = Image.open(BytesIO(conteudo))
        if imagem.mode not in ("RGB", "L"):
            imagem = imagem.convert("RGB")
        texto = pytesseract.image_to_string(
            imagem,
            lang=settings.OPENAI_LEGAL_ANALYSIS_OCR_LANG,
            config="--psm 6",
            timeout=settings.OPENAI_LEGAL_ANALYSIS_OCR_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        raise AnaliseJuridicaErro(f"Falha no OCR da imagem: {exc}") from exc

    return texto.strip()


def _extrair_de_bytes(conteudo, extensao):
    """Retorna (texto, paginas, metodo) a partir dos bytes de um documento."""
    if extensao in EXTENSOES_PDF:
        texto, paginas, metadata = _extrair_texto_pdf(conteudo)
        return texto, paginas, metadata.get("metodo_extracao", "nativo")
    if extensao in EXTENSOES_IMAGEM:
        return _ocr_imagem(conteudo), 1, "ocr_imagem"
    # Tenta PDF como último recurso (uploads sem extensão)
    if conteudo[:4] == b"%PDF":
        texto, paginas, metadata = _extrair_texto_pdf(conteudo)
        return texto, paginas, metadata.get("metodo_extracao", "nativo")
    raise AnaliseJuridicaErro(f"Formato não suportado para extração: {extensao or 'desconhecido'}")


def _fontes_do_imovel(imovel, imovel_caixa=None):
    """Lista de fontes a extrair: (chave, nome, fingerprint, tipo, origem).

    ``tipo`` é 'storage' (FieldFile) ou 'url' (str). A chave identifica a fonte
    no cache e o fingerprint detecta alterações.
    """
    fontes = []

    for arquivo in imovel.arquivos.all():
        if not arquivo.arquivo:
            continue
        extensao = _extensao(arquivo.arquivo.name)
        if extensao not in EXTENSOES_PDF and extensao not in EXTENSOES_IMAGEM:
            # Pula planilhas, docs etc. que o pipeline não lê
            continue
        fontes.append(
            {
                "chave": f"arquivo:{arquivo.pk}",
                "nome": arquivo.nome_exibicao,
                "categoria": arquivo.categoria,
                "fingerprint": arquivo.criado_em.isoformat(),
                "tipo": "storage",
                "origem": arquivo.arquivo,
                "extensao": extensao,
            }
        )

    categorias_anexadas = {f["categoria"] for f in fontes}
    if imovel_caixa:
        if imovel_caixa.matricula_url and "matricula" not in categorias_anexadas:
            fontes.append(
                {
                    "chave": "url:matricula",
                    "nome": "Matrícula (Caixa)",
                    "categoria": "matricula",
                    "fingerprint": imovel_caixa.matricula_url,
                    "tipo": "url",
                    "origem": imovel_caixa.matricula_url,
                    "extensao": ".pdf",
                }
            )
        if imovel_caixa.edital_url and "edital" not in categorias_anexadas:
            fontes.append(
                {
                    "chave": "url:edital",
                    "nome": "Edital (Caixa)",
                    "categoria": "edital",
                    "fingerprint": imovel_caixa.edital_url,
                    "tipo": "url",
                    "origem": imovel_caixa.edital_url,
                    "extensao": ".pdf",
                }
            )

    return fontes


def garantir_textos_documentos(imovel, imovel_caixa=None, *, forcar=False, permitir_playwright=True):
    """Extrai (com cache) o texto de todos os documentos do imóvel.

    Atualiza ``imovel.documentos_texto`` apenas quando há fontes novas/alteradas
    ou removidas. Retorna o dicionário do cache (chave -> dados do documento).

    ``permitir_playwright``: quando True, baixa documentos da Caixa bloqueados
    pelo anti-bot usando navegador (pesado). A análise (Celery) usa True; o chat
    (web) usa False e se apoia no texto já cacheado pela análise.
    """
    cache = dict(imovel.documentos_texto or {})
    fontes = _fontes_do_imovel(imovel, imovel_caixa)
    chaves_atuais = {f["chave"] for f in fontes}

    alterou = False

    # Remove do cache documentos que não existem mais
    for chave in list(cache.keys()):
        if chave not in chaves_atuais:
            cache.pop(chave, None)
            alterou = True

    for fonte in fontes:
        chave = fonte["chave"]
        registrado = cache.get(chave)
        # Reaproveita o cache só quando a extração anterior deu certo (sem erro).
        # Entradas que falharam (ex.: edital bloqueado pelo anti-bot) são
        # reprocessadas — permitindo o fallback via navegador numa nova tentativa.
        if (
            not forcar
            and registrado
            and registrado.get("fingerprint") == fonte["fingerprint"]
            and registrado.get("versao") == EXTRACAO_VERSION
            and not registrado.get("erro")
            and (registrado.get("texto") or "").strip()
        ):
            continue

        entrada = {
            "nome": fonte["nome"],
            "categoria": fonte["categoria"],
            "fingerprint": fonte["fingerprint"],
            "versao": EXTRACAO_VERSION,
            "texto": "",
            "paginas": 0,
            "metodo": "",
            "erro": "",
        }
        try:
            if fonte["tipo"] == "storage":
                conteudo = _ler_bytes_storage(fonte["origem"])
            else:
                conteudo = _baixar_url_documento(
                    fonte["origem"], imovel_caixa, permitir_playwright
                )
            texto, paginas, metodo = _extrair_de_bytes(conteudo, fonte["extensao"])
            entrada["texto"] = texto
            entrada["paginas"] = paginas
            entrada["metodo"] = metodo
            if not texto:
                entrada["erro"] = "Documento sem texto extraível, mesmo com OCR"
        except AnaliseJuridicaErro as exc:
            entrada["erro"] = str(exc)
        except Exception as exc:  # noqa: BLE001 - nunca derrubar o chat por um doc
            logger.exception("Falha ao extrair texto de %s (imovel %s)", chave, imovel.pk)
            entrada["erro"] = str(exc)[:300]

        cache[chave] = entrada
        alterou = True

    if alterou:
        imovel.documentos_texto = cache
        imovel.save(update_fields=["documentos_texto", "updated_at"])

    return cache
