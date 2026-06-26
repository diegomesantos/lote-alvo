import csv
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from django.db import close_old_connections
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from .models import ImovelCaixa
from .regras_despesas import extrair_regras_despesas

logger = logging.getLogger(__name__)

BASE_URL = "https://venda-imoveis.caixa.gov.br"
DOWNLOAD_LISTA_URL = f"{BASE_URL}/sistema/download-lista.asp"
DETALHE_URL = f"{BASE_URL}/sistema/detalhe-imovel.asp?hdnimovel={{imovel_id}}"

ESTADOS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]

MENSAGENS_IMOVEL_INDISPONIVEL = (
    "o imovel que voce procura nao esta mais disponivel para venda",
    "o imóvel que você procura não está mais disponível para venda",
    "nenhum imovel encontrado para o filtro selecionado",
    "nenhum imóvel encontrado para o filtro selecionado",
)


class ImovelCaixaIndisponivelError(RuntimeError):
    """A pagina de detalhe existe, mas a Caixa informa que o imovel saiu da venda."""


def _sync_playwright():
    # Import tardio: comandos que apenas consultam ou reprocessam o banco não
    # devem depender das bibliotecas nativas do Chromium.
    from playwright.sync_api import sync_playwright

    return sync_playwright()


def baixar_documento_caixa_playwright(doc_url, referer_url=None, headless=True, timeout_ms=60_000):
    """Baixa um documento (PDF) da Caixa usando um navegador real.

    O download direto via requests cai no anti-bot (Radware/CAPTCHA). Aqui
    visitamos uma página da Caixa para estabelecer os cookies do Radware e então
    baixamos o PDF pela sessão do navegador (context.request), que compartilha
    esses cookies. Retorna os bytes do documento.
    """
    with _sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        try:
            page = context.new_page()
            page.set_default_timeout(30_000)
            aquecimento = referer_url or f"{BASE_URL}/sistema/busca-imovel.asp?sltTipoBusca=imoveis"
            try:
                page.goto(aquecimento, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_timeout(1_500)
            except Exception as exc:  # noqa: BLE001 - aquecimento é best-effort
                logger.info("Aquecimento Radware falhou (%s); seguindo para o download", exc)

            resposta = context.request.get(doc_url, timeout=timeout_ms)
            if not resposta.ok:
                raise RuntimeError(f"HTTP {resposta.status} ao baixar documento da Caixa")
            return resposta.body()
        finally:
            browser.close()


def limpar_texto(valor) -> str:
    return " ".join(str(valor or "").replace("\xa0", " ").split()).strip()


def pagina_indisponivel_caixa(texto: str) -> bool:
    texto_normalizado = limpar_texto(texto).casefold()
    return any(mensagem in texto_normalizado for mensagem in MENSAGENS_IMOVEL_INDISPONIVEL)


def filtrar_detalhe_pendente(queryset):
    filtro_indisponivel = Q()
    for mensagem in MENSAGENS_IMOVEL_INDISPONIVEL:
        filtro_indisponivel |= Q(detalhes__detalhe_caixa__texto_extraido__icontains=mensagem)

    return queryset.filter(
        Q(detalhe_atualizado_em__isnull=True) | filtro_indisponivel
    )


def ordenar_detalhe_pendente(queryset):
    return queryset.annotate(
        _detalhe_pendente_prioridade=Case(
            When(detalhe_atualizado_em__isnull=False, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("_detalhe_pendente_prioridade", "estado", "cidade", "imovel_id_caixa")


def parse_decimal_br(valor, default=Decimal("0")) -> Decimal:
    texto = limpar_texto(valor).replace("R$", "").replace("%", "")
    if not texto:
        return default

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return default


def parse_date_br(valor):
    texto = limpar_texto(valor)
    if not texto:
        return None

    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_time_caixa(valor):
    texto = limpar_texto(valor).lower()
    match = re.search(r"(\d{1,2})h(\d{2})", texto)
    if not match:
        return None

    return datetime.strptime(f"{match.group(1)}:{match.group(2)}", "%H:%M").time()


def limitar(valor: str, tamanho: int) -> str:
    return limpar_texto(valor)[:tamanho]


def tipo_por_descricao(descricao: str) -> str:
    texto = limpar_texto(descricao).lower()
    if "apartamento" in texto:
        return "apto"
    if "casa" in texto:
        return "casa"
    if "sala" in texto or "comercial" in texto:
        return "sala"
    if "galp" in texto:
        return "galpao"
    if "terreno" in texto or "lote" in texto:
        return "lote"
    return "outro"


def extrair_numero(descricao: str, padrao: str):
    match = re.search(padrao, descricao, re.IGNORECASE)
    if not match:
        return None
    return parse_decimal_br(match.group(1), default=None)


def extrair_quartos(descricao: str):
    match = re.search(r"(\d+)\s*qto", descricao, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def ler_csv_caixa(caminho: str | Path) -> tuple[list[dict], dict]:
    caminho = Path(caminho)
    texto = caminho.read_bytes().decode("cp1252")
    linhas = texto.splitlines()
    reader = list(csv.reader(linhas, delimiter=";"))

    indice_cabecalho = None
    metadata = {"arquivo": str(caminho)}

    for indice, linha in enumerate(reader):
        limpa = [limpar_texto(coluna) for coluna in linha]
        if "Data de geração:" in limpa:
            posicao = limpa.index("Data de geração:")
            if len(limpa) > posicao + 1:
                metadata["data_geracao"] = parse_date_br(limpa[posicao + 1])
        if limpa and limpa[0].startswith("N° do imóvel"):
            indice_cabecalho = indice
            cabecalho = limpa
            break

    if indice_cabecalho is None:
        raise ValueError(f"Cabeçalho do CSV da Caixa não encontrado em {caminho}")

    registros = []
    for linha in reader[indice_cabecalho + 1:]:
        if not any(limpar_texto(coluna) for coluna in linha):
            continue
        dados = {
            cabecalho[indice]: limpar_texto(linha[indice]) if indice < len(linha) else ""
            for indice in range(len(cabecalho))
        }
        if dados.get("N° do imóvel"):
            registros.append(dados)

    metadata["total_registros"] = len(registros)
    return registros, metadata


def baixar_csv_caixa(estado: str = "geral", destino_dir: str | Path = "media/caixa_csv", headless=True) -> Path:
    destino_dir = Path(destino_dir)
    destino_dir.mkdir(parents=True, exist_ok=True)

    estado = estado.upper() if estado.lower() != "geral" else "geral"
    if estado != "geral" and estado not in ESTADOS:
        raise ValueError(f"Estado inválido: {estado}")

    with _sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            accept_downloads=True,
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(DOWNLOAD_LISTA_URL, wait_until="domcontentloaded", timeout=60_000)

        html = page.content()
        if "Radware Bot Manager CAPTCHA" in html or "perfdrive" in html:
            browser.close()
            raise RuntimeError("A Caixa exibiu CAPTCHA ao abrir a tela de download")

        page.wait_for_selector("#cmb_estado", timeout=20_000)
        page.select_option("#cmb_estado", estado)

        with page.expect_download(timeout=120_000) as download_info:
            page.click("#btn_next1")
        download = download_info.value

        destino = destino_dir / download.suggested_filename
        download.save_as(destino)
        browser.close()

    return destino


def defaults_csv_para_modelo(registro: dict, metadata: dict) -> dict:
    descricao = registro.get("Descrição", "")
    preco = parse_decimal_br(registro.get("Preço"))
    valor_avaliacao = parse_decimal_br(registro.get("Valor de avaliação"))
    desconto = parse_decimal_br(registro.get("Desconto"))
    financiamento = limpar_texto(registro.get("Financiamento")).lower() == "sim"

    return {
        "endereco": limitar(registro.get("Endereço"), 255),
        "bairro": limitar(registro.get("Bairro"), 100),
        "cidade": limitar(registro.get("Cidade"), 100),
        "estado": limitar(registro.get("UF"), 2).upper(),
        "tipo": tipo_por_descricao(descricao),
        "quartos": extrair_quartos(descricao),
        "area_total": extrair_numero(descricao, r"([\d.,]+)\s+de\s+área total"),
        "area_util": extrair_numero(descricao, r"([\d.,]+)\s+de\s+área privativa"),
        "area_terreno": extrair_numero(descricao, r"([\d.,]+)\s+de\s+área do terreno"),
        "descricao": descricao,
        "valor_avaliacao": valor_avaliacao,
        "percentual_desconto": desconto,
        "valor_minimo_lance": preco,
        "valor_final": preco,
        "tipo_leilao": "judicial" if "judicial" in registro.get("Modalidade de venda", "").lower() else "extra",
        "modalidade_venda": limitar(registro.get("Modalidade de venda"), 100),
        "formas_pagamento": {
            "a_vista": True,
            "financiamento": financiamento,
            "fgts": False,
            "consorcio": False,
            "parcelado": False,
        },
        "link_caixa": limitar(registro.get("Link de acesso"), 500),
        "data_geracao_lista": metadata.get("data_geracao"),
        "detalhes": {
            "csv": registro,
            "csv_metadata": {
                "arquivo": metadata.get("arquivo"),
                "data_geracao": metadata.get("data_geracao").isoformat() if metadata.get("data_geracao") else None,
            },
        },
    }


def _id_caixa_valido(imovel_id: str) -> bool:
    """O N° do imóvel da Caixa é sempre numérico (8–13 dígitos).

    O CSV às vezes vem com lixo na 1ª coluna — ex.: um warning de conversão
    de charset injetado pela ferramenta que gerou o arquivo. Esses valores não
    são IDs e estouravam o varchar(50) de imovel_id_caixa. Descartamos qualquer
    coisa que não seja um número plausível.
    """
    return imovel_id.isdigit() and 5 <= len(imovel_id) <= 20


def importar_csv_caixa(caminho: str | Path, limite: int | None = None) -> dict:
    registros, metadata = ler_csv_caixa(caminho)
    if limite:
        registros = registros[:limite]

    criados = 0
    atualizados = 0
    reativados = 0
    ignorados = 0
    ids = []
    sincronizacao = timezone.now()

    for registro in registros:
        imovel_id = limpar_texto(registro.get("N° do imóvel"))
        if not imovel_id:
            continue
        if not _id_caixa_valido(imovel_id):
            ignorados += 1
            logger.warning(
                "Linha do CSV da Caixa ignorada: N° do imóvel inválido (%r)",
                imovel_id[:60],
            )
            continue

        defaults = defaults_csv_para_modelo(registro, metadata)
        defaults["ativo_caixa"] = True
        defaults["ultima_sincronizacao_caixa"] = sincronizacao
        defaults["removido_da_caixa_em"] = None

        existente = ImovelCaixa.objects.filter(imovel_id_caixa=imovel_id).first()
        if existente:
            if not existente.ativo_caixa:
                reativados += 1

            detalhes_existentes = existente.detalhes or {}
            formas_existentes = existente.formas_pagamento or {}
            formas_csv = defaults.get("formas_pagamento", {})
            defaults["detalhes"] = {
                **detalhes_existentes,
                "csv": defaults["detalhes"].get("csv", {}),
                "csv_metadata": defaults["detalhes"].get("csv_metadata", {}),
            }
            defaults["formas_pagamento"] = {
                chave: bool(formas_csv.get(chave)) or bool(formas_existentes.get(chave))
                for chave in set(formas_csv) | set(formas_existentes)
            }

        obj, criado = ImovelCaixa.objects.update_or_create(
            imovel_id_caixa=imovel_id,
            defaults=defaults,
        )
        ids.append(obj.imovel_id_caixa)
        if criado:
            criados += 1
        else:
            atualizados += 1

    return {
        "criados": criados,
        "atualizados": atualizados,
        "reativados": reativados,
        "ignorados": ignorados,
        "ids": ids,
        "metadata": metadata,
    }


def marcar_imoveis_ausentes_como_inativos(
    ids_presentes: Iterable[str] | None = None,
    estado: str | None = None,
    sincronizacao=None,
    sincronizacao_inicio=None,
) -> int:
    ids = [
        limpar_texto(imovel_id)
        for imovel_id in (ids_presentes or [])
        if limpar_texto(imovel_id)
    ]
    if not ids and not sincronizacao_inicio:
        return 0

    sincronizacao = sincronizacao or timezone.now()
    queryset = ImovelCaixa.objects.filter(ativo_caixa=True)
    if estado and estado.lower() != "geral":
        queryset = queryset.filter(estado=estado.upper())
    if sincronizacao_inicio:
        queryset = queryset.filter(
            Q(ultima_sincronizacao_caixa__lt=sincronizacao_inicio) |
            Q(ultima_sincronizacao_caixa__isnull=True)
        )
    elif ids:
        queryset = queryset.exclude(imovel_id_caixa__in=ids)

    return (
        queryset
        .update(
            ativo_caixa=False,
            removido_da_caixa_em=sincronizacao,
            ultima_sincronizacao_caixa=sincronizacao,
        )
    )


def texto_pagina(soup: BeautifulSoup) -> str:
    alvo = soup.select_one("#dadosImovel") or soup.body or soup
    return "\n".join(
        linha.strip()
        for linha in alvo.get_text("\n").replace("\xa0", " ").splitlines()
        if linha.strip()
    )


def regex_um(texto: str, padrao: str):
    match = re.search(padrao, texto, re.IGNORECASE)
    return limpar_texto(match.group(1)) if match else ""


def extrair_documentos(soup: BeautifulSoup) -> dict:
    documentos = {}
    for link in soup.find_all("a"):
        onclick = link.get("onclick") or ""
        if "ExibeDoc" not in onclick:
            continue

        match = re.search(r"ExibeDoc\(['\"]([^'\"]+)", onclick)
        if not match:
            continue

        texto = limpar_texto(link.get_text(" ", strip=True)).lower()
        url = urljoin(BASE_URL, match.group(1))
        if "matr" in texto:
            documentos["matricula_url"] = url
        elif "edital" in texto:
            documentos["edital_url"] = url

    return documentos


def extrair_fotos(soup: BeautifulSoup) -> list[str]:
    fotos = []
    atributos = ("src", "data-src", "data-lazy-src", "href")
    for elemento in soup.find_all(["img", "source", "a"]):
        for atributo in atributos:
            valor = elemento.get(atributo) or ""
            if "/fotos/" not in valor.lower():
                continue
            url = urljoin(BASE_URL, valor)
            if url not in fotos:
                fotos.append(url)

    # Algumas versões da página carregam a galeria em JavaScript e não deixam
    # a URL em um atributo de <img>. Nesse caso, recuperamos os caminhos do HTML.
    for caminho in re.findall(
        r"(?:https?://venda-imoveis\.caixa\.gov\.br)?(/fotos/[^\"'\s)]+\.(?:jpe?g|png|webp))",
        str(soup),
        flags=re.IGNORECASE,
    ):
        url = urljoin(BASE_URL, caminho)
        if url not in fotos:
            fotos.append(url)
    return fotos


def extrair_datas_leilao(texto: str) -> list[dict]:
    datas = []
    padrao = r"Data\s+(?:do|da)\s*([^\n-]+)\s*-\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{1,2}h\d{2})"
    for label, data, hora in re.findall(padrao, texto, re.IGNORECASE):
        data_parseada = parse_date_br(data)
        hora_parseada = parse_time_caixa(hora)
        datas.append({
            "label": limpar_texto(label),
            "data": data_parseada.isoformat() if data_parseada else None,
            "hora": hora_parseada.strftime("%H:%M") if hora_parseada else None,
        })
    return datas


def extrair_secao(texto: str, inicio: str, fim: str | None = None) -> str:
    pos_inicio = texto.lower().find(inicio.lower())
    if pos_inicio == -1:
        return ""

    conteudo = texto[pos_inicio + len(inicio):]
    if fim:
        pos_fim = conteudo.lower().find(fim.lower())
        if pos_fim != -1:
            conteudo = conteudo[:pos_fim]
    return limpar_texto(conteudo)


def extrair_detalhes_html(html: str, url: str = "") -> dict:
    if "Radware Bot Manager CAPTCHA" in html or "perfdrive" in html:
        raise RuntimeError("A Caixa exibiu CAPTCHA na página de detalhe")

    soup = BeautifulSoup(html, "html.parser")
    texto = texto_pagina(soup)
    if pagina_indisponivel_caixa(texto):
        raise ImovelCaixaIndisponivelError("Imóvel não disponível na página de detalhe da Caixa")

    documentos = extrair_documentos(soup)
    fotos = extrair_fotos(soup)
    datas_leilao = extrair_datas_leilao(texto)

    descricao = extrair_secao(texto, "Descrição:", "FORMAS DE PAGAMENTO ACEITAS:")
    formas_texto = extrair_secao(texto, "FORMAS DE PAGAMENTO ACEITAS:", "REGRAS PARA PAGAMENTO")
    regras_texto = extrair_secao(texto, "REGRAS PARA PAGAMENTO DAS DESPESAS (caso existam):", "Baixar edital")
    leiloeiro_site = regex_um(html, r"SiteLeiloeiro\(&quot;([^&]+)&quot;\)")

    area_total = regex_um(texto, r"Área total\s*=\s*([\d.,]+)")
    area_privativa = regex_um(texto, r"Área privativa\s*=\s*([\d.,]+)")
    area_terreno = regex_um(texto, r"Área do terreno\s*=\s*([\d.,]+)")

    titulo = ""
    titulo_el = soup.select_one("#dadosImovel h5")
    if titulo_el:
        titulo = limpar_texto(titulo_el.get_text(" ", strip=True))

    dados = {
        "url": url,
        "titulo": titulo,
        "foto_url": fotos[0] if fotos else "",
        "fotos": fotos,
        "edital_url": documentos.get("edital_url", ""),
        "matricula_url": documentos.get("matricula_url", ""),
        "valor_avaliacao": regex_um(texto, r"Valor de avaliação:\s*R\$\s*([^\n]+)"),
        "valor_minimo_lance": regex_um(texto, r"Valor mínimo de venda[^:]*:\s*R\$\s*([^\n]+)"),
        "tipo_imovel": regex_um(texto, r"Tipo de imóvel:\s*([^\n]+)"),
        "quartos": regex_um(texto, r"Quartos:\s*(\d+)"),
        "numero_imovel_formatado": regex_um(texto, r"Número do imóvel:\s*([^\n]+)"),
        "matriculas": regex_um(texto, r"Matrícula\(s\):\s*([^\n]+)"),
        "comarca": regex_um(texto, r"Comarca:\s*([^\n]+)"),
        "oficio": regex_um(texto, r"Ofício:\s*([^\n]+)"),
        "inscricao_imobiliaria": regex_um(texto, r"Inscrição imobiliária:\s*([^\n]+)"),
        "averbacao_leiloes_negativos": regex_um(texto, r"Averbação dos leilões negativos:\s*([^\n]+)"),
        "area_total": area_total,
        "area_privativa": area_privativa,
        "area_terreno": area_terreno,
        "edital": regex_um(texto, r"Edital:\s*([^\n]+)"),
        "numero_item": regex_um(texto, r"Número do item:\s*([^\n]+)"),
        "leiloeiro": regex_um(texto, r"Leiloeiro\(a\):\s*([^\n]+)"),
        "leiloeiro_site": leiloeiro_site,
        "datas_leilao": datas_leilao,
        "descricao": descricao,
        "formas_pagamento_texto": formas_texto,
        "regras_pagamento_texto": regras_texto,
        "edital_publicado_em": regex_um(texto, r"Edital publicado em:\s*([^)]+)"),
        "texto_extraido": texto,
    }

    return dados


def aplicar_detalhes(imovel: ImovelCaixa, detalhes: dict) -> ImovelCaixa:
    fotos = detalhes.get("fotos") or []
    formas_pagamento = dict(imovel.formas_pagamento or {})
    formas_texto = detalhes.get("formas_pagamento_texto", "").lower()

    if "recursos próprios" in formas_texto:
        formas_pagamento["a_vista"] = True
    if "fgts" in formas_texto:
        formas_pagamento["fgts"] = True
    if "financiamento" in formas_texto:
        formas_pagamento["financiamento"] = True

    if detalhes.get("valor_avaliacao"):
        imovel.valor_avaliacao = parse_decimal_br(detalhes["valor_avaliacao"], imovel.valor_avaliacao)
    if detalhes.get("valor_minimo_lance"):
        imovel.valor_minimo_lance = parse_decimal_br(detalhes["valor_minimo_lance"], imovel.valor_minimo_lance)
        imovel.valor_final = imovel.valor_minimo_lance
    if detalhes.get("tipo_imovel"):
        imovel.tipo = tipo_por_descricao(detalhes["tipo_imovel"])
    if detalhes.get("quartos"):
        imovel.quartos = int(detalhes["quartos"])
    if detalhes.get("area_total"):
        imovel.area_total = parse_decimal_br(detalhes["area_total"], imovel.area_total)
    if detalhes.get("area_privativa"):
        imovel.area_util = parse_decimal_br(detalhes["area_privativa"], imovel.area_util)
    if detalhes.get("area_terreno"):
        imovel.area_terreno = parse_decimal_br(detalhes["area_terreno"], imovel.area_terreno)
    if detalhes.get("descricao"):
        imovel.descricao = detalhes["descricao"]

    if fotos:
        imovel.foto_url = fotos[0]
    if detalhes.get("edital_url"):
        imovel.edital_url = detalhes["edital_url"]
    if detalhes.get("matricula_url"):
        imovel.matricula_url = detalhes["matricula_url"]
    if detalhes.get("url"):
        imovel.link_caixa = detalhes["url"]

    if detalhes.get("datas_leilao"):
        primeira_data = detalhes["datas_leilao"][0]
        if primeira_data.get("data"):
            imovel.data_leilao = datetime.strptime(primeira_data["data"], "%Y-%m-%d").date()
        if primeira_data.get("hora"):
            imovel.hora_leilao = datetime.strptime(primeira_data["hora"], "%H:%M").time()

    texto = detalhes.get("texto_extraido", "").lower()
    if "ocupado" in texto:
        imovel.ocupado = True
        imovel.situacao = "Ocupado"
    elif not imovel.situacao:
        imovel.ocupado = False

    imovel.possui_penhora = "penhora" in texto
    imovel.formas_pagamento = formas_pagamento

    regras_despesas = extrair_regras_despesas(detalhes.get("regras_pagamento_texto", ""))
    imovel.despesa_condominio = regras_despesas["despesa_condominio"]
    imovel.despesa_tributos = regras_despesas["despesa_tributos"]
    imovel.detalhes = {
        **(imovel.detalhes or {}),
        "detalhe_caixa": detalhes,
    }
    imovel.detalhe_atualizado_em = timezone.now()
    imovel.save()
    return imovel


def aplicar_detalhes_por_pk(imovel_pk: int, detalhes: dict) -> ImovelCaixa:
    close_old_connections()
    try:
        imovel = ImovelCaixa.objects.get(pk=imovel_pk)
        return aplicar_detalhes(imovel, detalhes)
    finally:
        close_old_connections()


def inativar_imovel_indisponivel_por_pk(imovel_pk: int, motivo: str, url: str) -> ImovelCaixa:
    close_old_connections()
    try:
        imovel = ImovelCaixa.objects.get(pk=imovel_pk)
        agora = timezone.now()
        detalhes = dict(imovel.detalhes or {})
        detalhes["detalhe_caixa_indisponivel"] = {
            "motivo": motivo,
            "url": url,
            "verificado_em": agora.isoformat(),
        }
        imovel.ativo_caixa = False
        imovel.removido_da_caixa_em = agora
        imovel.ultima_sincronizacao_caixa = agora
        imovel.detalhes = detalhes
        imovel.save(
            update_fields=[
                "ativo_caixa",
                "removido_da_caixa_em",
                "ultima_sincronizacao_caixa",
                "detalhes",
                "atualizado_em",
            ]
        )
        return imovel
    finally:
        close_old_connections()


def enriquecer_imoveis_caixa(imoveis: Iterable[ImovelCaixa], intervalo=1.0, headless=True) -> dict:
    erros = []
    atualizados = 0
    inativados = 0

    with _sync_playwright() as playwright, ThreadPoolExecutor(max_workers=1) as executor:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        for imovel in imoveis:
            url = imovel.link_caixa or DETALHE_URL.format(imovel_id=imovel.imovel_id_caixa)
            try:
                logger.info("Enriquecendo imóvel Caixa %s", imovel.imovel_id_caixa)
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_timeout(2_000)
                detalhes = extrair_detalhes_html(page.content(), url=page.url)
                executor.submit(aplicar_detalhes_por_pk, imovel.pk, detalhes).result()
                atualizados += 1
                logger.info("Imóvel Caixa %s enriquecido com sucesso", imovel.imovel_id_caixa)
            except ImovelCaixaIndisponivelError as exc:
                executor.submit(
                    inativar_imovel_indisponivel_por_pk,
                    imovel.pk,
                    str(exc),
                    page.url,
                ).result()
                inativados += 1
                logger.info(
                    "Imóvel Caixa %s inativado durante enriquecimento: %s",
                    imovel.imovel_id_caixa,
                    exc,
                )
            except Exception as exc:
                logger.exception("Erro ao enriquecer imóvel %s", imovel.imovel_id_caixa)
                erros.append(f"{imovel.imovel_id_caixa}: {exc}")

            if intervalo:
                time.sleep(intervalo)

        browser.close()

    return {"atualizados": atualizados, "inativados": inativados, "erros": erros}
