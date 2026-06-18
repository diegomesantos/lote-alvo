import re
import unicodedata

from django.db import migrations


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return " ".join(texto.casefold().replace("\xa0", " ").split())


def _classificar(trecho):
    texto = _normalizar(trecho)
    if not texto:
        return "indeterminado"
    tem_comprador = any(
        termo in texto for termo in ("comprador", "adquirente", "arrematante")
    )
    tem_caixa = "caixa" in texto
    if tem_comprador and tem_caixa and re.search(r"\b10\s*%", texto):
        return "comprador_ate_10"
    if tem_comprador:
        return "comprador"
    if tem_caixa:
        return "caixa"
    return "indeterminado"


def _extrair_trecho(texto, rotulo, proximo_rotulo):
    match = re.search(
        rf"\b{rotulo}\s*:\s*(.*?)"
        rf"(?=\b{proximo_rotulo}\s*:|\bcorretores?\s+credenciados?\b|"
        rf"\bregras?\s+da\s+venda\b|\bformas?\s+de\s+pagamento\b|$)",
        texto,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _extrair_regras(texto_original):
    texto = _normalizar(texto_original)
    resultado = {
        "despesa_condominio": "indeterminado",
        "despesa_tributos": "indeterminado",
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
        classificacao = _classificar(combinado.group(1))
        resultado["despesa_condominio"] = classificacao
        resultado["despesa_tributos"] = classificacao

    condominio = _extrair_trecho(texto, "condominio", "tributos?")
    tributos = _extrair_trecho(texto, "tributos?", "condominio")
    if condominio:
        resultado["despesa_condominio"] = _classificar(condominio)
    if tributos:
        resultado["despesa_tributos"] = _classificar(tributos)
    return resultado


def preencher_regras(apps, schema_editor):
    ImovelCaixa = apps.get_model("leiloes", "ImovelCaixa")
    pendentes = []
    queryset = ImovelCaixa.objects.filter(
        detalhe_atualizado_em__isnull=False,
    ).only("id", "detalhes", "despesa_condominio", "despesa_tributos")

    for imovel in queryset.iterator(chunk_size=500):
        detalhe_caixa = (imovel.detalhes or {}).get("detalhe_caixa") or {}
        regras_texto = detalhe_caixa.get("regras_pagamento_texto") or ""
        if not regras_texto.strip():
            continue

        regras = _extrair_regras(regras_texto)
        if (
            imovel.despesa_condominio == regras["despesa_condominio"]
            and imovel.despesa_tributos == regras["despesa_tributos"]
        ):
            continue

        imovel.despesa_condominio = regras["despesa_condominio"]
        imovel.despesa_tributos = regras["despesa_tributos"]
        pendentes.append(imovel)

        if len(pendentes) >= 500:
            ImovelCaixa.objects.bulk_update(
                pendentes,
                ["despesa_condominio", "despesa_tributos"],
                batch_size=500,
            )
            pendentes.clear()

    if pendentes:
        ImovelCaixa.objects.bulk_update(
            pendentes,
            ["despesa_condominio", "despesa_tributos"],
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("leiloes", "0005_imovelcaixa_despesa_condominio_tributos"),
    ]

    operations = [
        migrations.RunPython(preencher_regras, migrations.RunPython.noop),
    ]
