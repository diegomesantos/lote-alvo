import re
import unicodedata


VALOR_INDETERMINADO = "indeterminado"


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return " ".join(texto.casefold().replace("\xa0", " ").split())


def _classificar_despesa(trecho: str) -> str:
    """Classifica quem assume a despesa a partir do texto publicado pela Caixa."""
    texto = _normalizar(trecho)
    if not texto:
        return VALOR_INDETERMINADO

    tem_comprador = any(
        termo in texto
        for termo in ("comprador", "adquirente", "arrematante")
    )
    tem_caixa = "caixa" in texto
    tem_regra_10 = bool(re.search(r"\b10\s*%", texto))

    # A Caixa publica duas redações equivalentes: comprador "até o limite de
    # 10%" ou comprador quando o débito é "inferior a 10%", com a Caixa
    # assumindo o excedente. Ambas pertencem à mesma opção de filtro.
    if tem_comprador and tem_caixa and tem_regra_10:
        return "comprador_ate_10"
    if tem_comprador:
        return "comprador"
    if tem_caixa:
        return "caixa"
    return VALOR_INDETERMINADO


def _extrair_trecho(texto: str, rotulo: str, proximo_rotulo: str) -> str:
    padrao = (
        rf"\b{rotulo}\s*:\s*(.*?)"
        rf"(?=\b{proximo_rotulo}\s*:|\bcorretores?\s+credenciados?\b|"
        rf"\bregras?\s+da\s+venda\b|\bformas?\s+de\s+pagamento\b|$)"
    )
    match = re.search(padrao, texto, re.DOTALL)
    return match.group(1).strip() if match else ""


def extrair_regras_despesas(regras_texto: str) -> dict[str, str]:
    """Estrutura as regras de condomínio e tributos da página do imóvel.

    Aceita as redações separadas ("Condomínio: ... Tributos: ...") e a forma
    combinada usada pela Caixa ("Tributos e condomínio: ...").
    """
    texto = _normalizar(regras_texto)
    resultado = {
        "despesa_condominio": VALOR_INDETERMINADO,
        "despesa_tributos": VALOR_INDETERMINADO,
    }
    if not texto:
        return resultado

    combinado = re.search(
        r"\b(?:tributos?\s+e\s+condominio|condominio\s+e\s+tributos?)\s*:\s*(.*?)"
        r"(?=\bcorretores?\s+credenciados?\b|\bregras?\s+da\s+venda\b|"
        r"\bformas?\s+de\s+pagamento\b|$)",
        texto,
        re.DOTALL,
    )
    if combinado:
        classificacao = _classificar_despesa(combinado.group(1))
        resultado["despesa_condominio"] = classificacao
        resultado["despesa_tributos"] = classificacao

    trecho_condominio = _extrair_trecho(texto, "condominio", "tributos?")
    trecho_tributos = _extrair_trecho(texto, "tributos?", "condominio")

    if trecho_condominio:
        resultado["despesa_condominio"] = _classificar_despesa(trecho_condominio)
    if trecho_tributos:
        resultado["despesa_tributos"] = _classificar_despesa(trecho_tributos)

    return resultado
