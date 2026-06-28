"""
Tabelas de emolumentos de Escritura e Registro de Imóveis por estado.
Fonte: Tribunais de Justiça Estaduais — tabelas 2025/2026
Valores são estimativas; confirme sempre com o cartório competente.

Estrutura de cada tabela:
  Lista de tuplas (limite_superior, valor_fixo)
  O último item tem limite_superior = float('inf')
  A lógica é: se base <= limite, usa esse valor fixo.
"""
from datetime import date

# ─── Bahia (BA) — TJ-BA ─────────────────────────────────────────────────────
# Idêntico para escritura e registro na regra operacional adotada.
TABELA_BA = [
    (1_600.00,       319.12),
    (3_200.00,       401.40),
    (8_000.00,       483.68),
    (12_000.00,      522.76),
    (16_000.00,      562.54),
    (24_000.00,      642.22),
    (32_000.00,      723.98),
    (47_000.00,      799.68),
    (63_000.00,      881.24),
    (78_000.00,      967.68),
    (118_000.00,   1_030.66),
    (160_000.00,   1_115.10),
    (235_000.00,   1_805.16),
    (350_000.00,   2_708.06),
    (530_000.00,   4_067.28),
    (800_000.00,   6_099.38),
    (1_200_000.00, 9_147.62),
    (1_800_000.00,10_977.08),
    (2_700_000.00,14_270.54),
    (4_000_000.00,18_551.00),
    (float('inf'),24_117.28),
]

# ─── São Paulo (SP) — TJ-SP 2026 ────────────────────────────────────────────
# Tabela oficial TJ-SP (registro de imóveis e escritura têm tabelas distintas)
TABELA_SP_ESCRITURA = [
    (5_430.37,        319.12),
    (10_860.75,       401.40),
    (21_721.49,       483.68),
    (36_202.49,       522.76),
    (54_303.74,       562.54),
    (72_404.98,       642.22),
    (90_506.23,       723.98),
    (108_607.48,      799.68),
    (180_756.25,    1_115.10),  # faixas intermediárias simplificadas TJ-SP
    (361_512.47,    4_165.35),
    (723_024.94,    5_694.22),
    (1_446_049.88, 10_152.56),
    (float('inf'), 14_610.89),
]

TABELA_SP_REGISTRO = [
    (5_430.37,        263.92),
    (10_860.75,       331.62),
    (21_721.49,       399.30),
    (36_202.49,       431.89),
    (54_303.74,       464.73),
    (72_404.98,       530.40),
    (90_506.23,       597.89),
    (108_607.48,      660.58),
    (180_756.25,      920.69),
    (361_512.47,    3_232.83),
    (723_024.94,    4_452.39),
    (1_446_049.88,  7_921.32),
    (float('inf'), 11_390.25),
]

# ─── Rio de Janeiro (RJ) — TJ-RJ 2026 ───────────────────────────────────────
# Inclui FUNDPERJ (0,1% sobre o valor) cobrado adicionalmente
TABELA_RJ = [
    (3_000.00,        198.73),
    (6_000.00,        249.90),
    (12_000.00,       315.30),
    (24_000.00,       397.53),
    (36_000.00,       500.70),
    (48_000.00,       630.88),
    (72_000.00,       795.11),
    (96_000.00,     1_001.56),
    (144_000.00,    1_261.73),
    (192_000.00,    1_589.48),
    (288_000.00,    2_003.08),
    (384_000.00,    2_523.88),
    (576_000.00,    3_180.58),
    (768_000.00,    4_007.49),
    (1_152_000.00,  5_049.45),
    (1_536_000.00,  6_362.28),
    (2_304_000.00,  8_016.45),
    (float('inf'), 10_100.50),
]
RJ_FUNDPERJ_PCT = 0.001  # 0,1%

# ─── Minas Gerais (MG) — TJ-MG 2026 ─────────────────────────────────────────
TABELA_MG = [
    (3_000.00,        221.55),
    (6_000.00,        278.58),
    (12_000.00,       351.38),
    (24_000.00,       442.66),
    (36_000.00,       557.57),
    (60_000.00,       702.45),
    (90_000.00,       885.04),
    (120_000.00,    1_115.01),
    (180_000.00,    1_405.08),
    (240_000.00,    1_770.46),
    (360_000.00,    2_231.05),
    (480_000.00,    2_811.15),
    (720_000.00,    3_542.55),
    (960_000.00,    4_464.07),
    (1_440_000.00,  5_625.00),
    (float('inf'),  7_088.52),
]

# ─── Paraná (PR) — TJ-PR 2026 ────────────────────────────────────────────────
# Inclui FUNREJUS (0,2% sobre o valor)
TABELA_PR = [
    (3_000.00,        213.96),
    (6_000.00,        269.15),
    (12_000.00,       339.19),
    (18_000.00,       427.35),
    (30_000.00,       538.58),
    (45_000.00,       678.69),
    (60_000.00,       855.28),
    (90_000.00,     1_077.80),
    (120_000.00,    1_358.40),
    (180_000.00,    1_711.99),
    (240_000.00,    2_157.15),
    (360_000.00,    2_718.64),
    (480_000.00,    3_425.74),
    (720_000.00,    4_316.40),
    (float('inf'),  5_438.99),
]
PR_FUNREJUS_PCT = 0.002  # 0,2%

# ─── Rio Grande do Sul (RS) — TJ-RS 2026 (índice IEPE/UFRGS +5,86%) ─────────
TABELA_RS = [
    (3_000.00,        202.37),
    (6_000.00,        254.60),
    (12_000.00,       320.87),
    (24_000.00,       404.32),
    (36_000.00,       509.44),
    (60_000.00,       641.97),
    (90_000.00,       809.09),
    (120_000.00,    1_019.45),
    (180_000.00,    1_284.52),
    (240_000.00,    1_618.86),
    (360_000.00,    2_040.09),
    (480_000.00,    2_570.60),
    (720_000.00,    3_239.08),
    (float('inf'),  4_081.15),
]

# ─── Pernambuco (PE) — TJ-PE 2025 ────────────────────────────────────────────
TABELA_PE = [
    (2_000.00,        218.40),
    (4_000.00,        274.68),
    (8_000.00,        346.15),
    (16_000.00,       436.06),
    (24_000.00,       549.41),
    (40_000.00,       692.29),
    (60_000.00,       872.40),
    (80_000.00,     1_099.38),
    (120_000.00,    1_385.42),
    (160_000.00,    1_746.01),
    (240_000.00,    2_200.07),
    (320_000.00,    2_772.36),
    (480_000.00,    3_493.34),
    (640_000.00,    4_401.68),
    (float('inf'),  5_547.98),
]

# ─── Ceará (CE) — TJ-CE 2025 ──────────────────────────────────────────────────
TABELA_CE = [
    (2_000.00,        196.56),
    (4_000.00,        247.28),
    (8_000.00,        311.57),
    (16_000.00,       392.52),
    (24_000.00,       494.58),
    (40_000.00,       623.12),
    (60_000.00,       785.14),
    (80_000.00,       989.21),
    (120_000.00,    1_246.52),
    (160_000.00,    1_571.01),
    (240_000.00,    1_980.37),
    (320_000.00,    2_495.34),
    (480_000.00,    3_144.33),
    (float('inf'),  3_961.72),
]

# ─── Distrito Federal (DF) — TJDFT 2025 ──────────────────────────────────────
TABELA_DF = [
    (3_000.00,        298.61),
    (6_000.00,        375.80),
    (12_000.00,       473.34),
    (24_000.00,       596.32),
    (36_000.00,       751.09),
    (60_000.00,       946.32),
    (90_000.00,     1_192.25),
    (120_000.00,    1_502.18),
    (180_000.00,    1_892.81),
    (240_000.00,    2_385.38),
    (360_000.00,    3_005.50),
    (480_000.00,    3_788.67),
    (720_000.00,    4_774.38),
    (float('inf'),  6_016.46),
]

# ─── Santa Catarina (SC) — TJ-SC 2025 ─────────────────────────────────────────
TABELA_SC = [
    (2_000.00,        197.45),
    (4_000.00,        248.53),
    (8_000.00,        313.19),
    (16_000.00,       394.76),
    (24_000.00,       497.38),
    (40_000.00,       626.58),
    (60_000.00,       789.68),
    (80_000.00,       995.09),
    (120_000.00,    1_254.22),
    (160_000.00,    1_580.51),
    (240_000.00,    1_991.37),
    (320_000.00,    2_509.20),
    (480_000.00,    3_161.86),
    (640_000.00,    3_983.77),
    (float('inf'),  5_020.45),
]

# ─── Goiás (GO) — TJ-GO 2025 ───────────────────────────────────────────────────
TABELA_GO = [
    (2_000.00,        204.18),
    (4_000.00,        256.90),
    (8_000.00,        323.65),
    (16_000.00,       407.68),
    (24_000.00,       513.82),
    (40_000.00,       647.27),
    (60_000.00,       815.88),
    (80_000.00,     1_028.12),
    (120_000.00,    1_295.65),
    (160_000.00,    1_633.02),
    (240_000.00,    2_057.20),
    (320_000.00,    2_592.23),
    (480_000.00,    3_266.45),
    (640_000.00,    4_117.18),
    (float('inf'),  5_188.72),
]

# ─── Espírito Santo (ES) — TJ-ES 2025 ──────────────────────────────────────────
TABELA_ES = [
    (2_000.00,        191.34),
    (4_000.00,        240.82),
    (8_000.00,        303.61),
    (16_000.00,       382.55),
    (24_000.00,       482.14),
    (40_000.00,       607.47),
    (60_000.00,       765.57),
    (80_000.00,       964.78),
    (120_000.00,    1_215.68),
    (160_000.00,    1_531.80),
    (240_000.00,    1_930.21),
    (320_000.00,    2_432.26),
    (480_000.00,    3_065.54),
    (640_000.00,    3_863.97),
    (float('inf'),  4_869.33),
]

# ─── Índice geral de estados disponíveis ────────────────────────────────────
# Para estados não cobertos, usamos uma estimativa genérica (0.5% do valor)
ESTADOS_DISPONIVEIS = {
    "BA": {"escritura": TABELA_BA,    "registro": TABELA_BA,    "extra": None},
    "SP": {"escritura": TABELA_SP_ESCRITURA, "registro": TABELA_SP_REGISTRO, "extra": None},
    "RJ": {"escritura": TABELA_RJ,    "registro": TABELA_RJ,    "extra": ("FUNDPERJ", RJ_FUNDPERJ_PCT)},
    "MG": {"escritura": TABELA_MG,    "registro": TABELA_MG,    "extra": None},
    "PR": {"escritura": TABELA_PR,    "registro": TABELA_PR,    "extra": ("FUNREJUS", PR_FUNREJUS_PCT)},
    "RS": {"escritura": TABELA_RS,    "registro": TABELA_RS,    "extra": None},
    "PE": {"escritura": TABELA_PE,    "registro": TABELA_PE,    "extra": None},
    "CE": {"escritura": TABELA_CE,    "registro": TABELA_CE,    "extra": None},
    "DF": {"escritura": TABELA_DF,    "registro": TABELA_DF,    "extra": None},
    "SC": {"escritura": TABELA_SC,    "registro": TABELA_SC,    "extra": None},
    "GO": {"escritura": TABELA_GO,    "registro": TABELA_GO,    "extra": None},
    "ES": {"escritura": TABELA_ES,    "registro": TABELA_ES,    "extra": None},
}

LISTA_ESTADOS = sorted(ESTADOS_DISPONIVEIS.keys())

ESTADOS_NOMES = {
    "AC":"Acre","AL":"Alagoas","AM":"Amazonas","AP":"Amapá","BA":"Bahia",
    "CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás",
    "MA":"Maranhão","MG":"Minas Gerais","MS":"Mato Grosso do Sul",
    "MT":"Mato Grosso","PA":"Pará","PB":"Paraíba","PE":"Pernambuco",
    "PI":"Piauí","PR":"Paraná","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte",
    "RO":"Rondônia","RR":"Roraima","RS":"Rio Grande do Sul",
    "SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins",
}

TODOS_ESTADOS = sorted(ESTADOS_NOMES.keys())


def _hoje():
    return date.today()


def _vigente_qs(queryset, data_referencia):
    from django.db.models import Q

    return queryset.filter(
        ativo=True,
        vigente_inicio__lte=data_referencia,
    ).filter(
        Q(vigente_fim__isnull=True) | Q(vigente_fim__gte=data_referencia)
    )


def _buscar_tabela_db(uf, tipo, data_referencia=None):
    data_referencia = data_referencia or _hoje()
    try:
        from django.db.utils import OperationalError, ProgrammingError
        from apps.calculadora.models import CartorioTabela

        queryset = CartorioTabela.objects.filter(uf=uf, tipo=tipo)
        return (
            _vigente_qs(queryset, data_referencia)
            .prefetch_related("faixas")
            .order_by("-vigente_inicio", "-ano", "-id")
            .first()
        )
    except (ImportError, OperationalError, ProgrammingError):
        return None


def _buscar_extra_db(uf, data_referencia=None):
    data_referencia = data_referencia or _hoje()
    try:
        from django.db.utils import OperationalError, ProgrammingError
        from apps.calculadora.models import CartorioRegraExtra

        queryset = CartorioRegraExtra.objects.filter(uf=uf)
        return (
            _vigente_qs(queryset, data_referencia)
            .order_by("-vigente_inicio", "-ano", "-id")
            .first()
        )
    except (ImportError, OperationalError, ProgrammingError):
        return None


def _tabela_db_para_tuplas(tabela):
    if not tabela:
        return None
    faixas = list(tabela.faixas.all().order_by("ordem"))
    if not faixas:
        return None
    return [
        (
            float("inf") if faixa.limite_superior is None else float(faixa.limite_superior),
            float(faixa.valor),
        )
        for faixa in faixas
    ]


def _fonte_tabela(tabela):
    if not tabela:
        return None
    return {
        "uf": tabela.uf,
        "ano": tabela.ano,
        "tipo": tabela.tipo,
        "status": tabela.status,
        "fonte_nome": tabela.fonte_nome,
        "fonte_url": tabela.fonte_url,
        "fundamento": tabela.fundamento,
        "vigencia": tabela.vigente_label,
    }


def _fonte_extra(extra):
    if not extra:
        return None
    return {
        "uf": extra.uf,
        "ano": extra.ano,
        "tipo": "extra",
        "status": extra.status,
        "fonte_nome": extra.fonte_nome,
        "fonte_url": extra.fonte_url,
        "fundamento": extra.fundamento,
        "vigencia": extra.vigente_label,
        "nome": extra.nome,
    }


def _calcular_cartorio_db(estado, base, tipo_leilao="Extrajudicial", data_referencia=None):
    uf = estado.upper() if estado else "BA"
    tabela_registro = _buscar_tabela_db(uf, "registro", data_referencia)
    tab_registro = _tabela_db_para_tuplas(tabela_registro)
    if not tab_registro:
        return None

    tabela_escritura = None
    tab_escritura = None
    if tipo_leilao != "Judicial":
        tabela_escritura = _buscar_tabela_db(uf, "escritura", data_referencia)
        tab_escritura = _tabela_db_para_tuplas(tabela_escritura)
        if not tab_escritura:
            return None

    if tipo_leilao == "Judicial":
        escritura_val = 0
        escritura_faixa = "Carta de arrematação (isenta de escritura pública)"
    else:
        escritura_val, escritura_faixa, _ = buscar_faixa(tab_escritura, base)

    registro_val, registro_faixa, _ = buscar_faixa(tab_registro, base)

    extra = _buscar_extra_db(uf, data_referencia)
    extra_val = 0
    extra_nome = None
    if extra:
        extra_nome = extra.nome
        extra_val = base * float(extra.percentual) / 100

    fontes = [
        fonte for fonte in (
            _fonte_tabela(tabela_escritura),
            _fonte_tabela(tabela_registro),
            _fonte_extra(extra),
        )
        if fonte
    ]
    fonte_principal = fontes[0] if fontes else {}
    status_pendente = any(fonte.get("status") == "pendente_validacao" for fonte in fontes)
    aviso = None
    if status_pendente:
        aviso = "Tabela cartorária versionada pendente de validação formal da fonte oficial."

    return dict(
        escritura=escritura_val,
        registro=registro_val,
        extra=extra_val,
        extra_nome=extra_nome,
        total=escritura_val + registro_val + extra_val,
        escritura_faixa=escritura_faixa,
        registro_faixa=registro_faixa,
        aviso=aviso,
        origem="banco",
        fonte_nome=fonte_principal.get("fonte_nome", ""),
        fonte_url=fonte_principal.get("fonte_url", ""),
        fonte_ano=fonte_principal.get("ano"),
        fonte_status=fonte_principal.get("status", ""),
        fonte_vigencia=fonte_principal.get("vigencia", ""),
        fontes=fontes,
    )


def obter_tabelas_cartorio(estado, tipo_leilao="Extrajudicial", data_referencia=None):
    """Retorna tabelas para exibição, preferindo dados versionados do banco."""
    uf = estado.upper() if estado else "BA"
    tabela_registro = _buscar_tabela_db(uf, "registro", data_referencia)
    tab_registro = _tabela_db_para_tuplas(tabela_registro)
    tabela_escritura = None
    tab_escritura = None
    if tipo_leilao != "Judicial":
        tabela_escritura = _buscar_tabela_db(uf, "escritura", data_referencia)
        tab_escritura = _tabela_db_para_tuplas(tabela_escritura)

    if tab_registro and (tipo_leilao == "Judicial" or tab_escritura):
        return {
            "escritura": tab_escritura,
            "registro": tab_registro,
            "origem": "banco",
            "fontes": [
                fonte for fonte in (
                    _fonte_tabela(tabela_escritura),
                    _fonte_tabela(tabela_registro),
                )
                if fonte
            ],
        }

    if uf in ESTADOS_DISPONIVEIS:
        dados = ESTADOS_DISPONIVEIS[uf]
        return {
            "escritura": None if tipo_leilao == "Judicial" else dados["escritura"],
            "registro": dados["registro"],
            "origem": "codigo",
            "fontes": [],
        }

    return {"escritura": None, "registro": None, "origem": "estimativa", "fontes": []}


def buscar_faixa(tabela, base):
    """Retorna (valor_emolumento, faixa_texto, indice_faixa)"""
    for i,(limite, valor) in enumerate(tabela):
        if base <= limite:
            limite_ant = tabela[i-1][0] if i > 0 else 0.0
            if limite == float('inf'):
                faixa = f"Acima de R$ {tabela[-2][0]:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            else:
                faixa = f"R$ {limite_ant:,.2f} — R$ {limite:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            return valor, faixa, i
    # fallback: última faixa
    valor = tabela[-1][1]
    faixa = f"Acima de R$ {tabela[-2][0]:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return valor, faixa, len(tabela)-1


def calcular_cartorio(estado, base, tipo_leilao="Extrajudicial"):
    """
    Retorna dict com escritura, registro, extra e total.
    Para leilão judicial extrajudicial, a carta de arrematação substitui a escritura
    mas o registro da carta ainda é necessário (usa tabela de registro).
    """
    uf = estado.upper() if estado else "BA"

    calculo_db = _calcular_cartorio_db(uf, base, tipo_leilao)
    if calculo_db:
        return calculo_db

    if uf in ESTADOS_DISPONIVEIS:
        dados = ESTADOS_DISPONIVEIS[uf]
        tab_escritura = dados["escritura"]
        tab_registro  = dados["registro"]
        extra_info    = dados["extra"]
    else:
        # Estado sem tabela específica: estimativa 0,5% do valor para cada
        val_est = base * 0.005
        return dict(
            escritura=0,           # carta de arrematação dispensada em judicial
            registro=val_est,
            extra=0,
            extra_nome=None,
            total=val_est,
            escritura_faixa="Estimativa (estado sem tabela)",
            registro_faixa="Estimativa (0,5% do valor)",
            aviso=f"⚠️ Tabela oficial de {uf} não disponível. Valores estimados em 0,5%.",
            origem="estimativa",
            fonte_nome="Estimativa interna",
            fonte_url="",
            fonte_ano=None,
            fonte_status="estimativa",
            fonte_vigencia="",
            fontes=[],
        )

    # Escritura: só em compra e venda direta; leilão judicial usa carta de arrematação
    if tipo_leilao == "Judicial":
        escritura_val   = 0
        escritura_faixa = "Carta de arrematação (isenta de escritura pública)"
    else:
        escritura_val, escritura_faixa, _ = buscar_faixa(tab_escritura, base)

    registro_val, registro_faixa, _ = buscar_faixa(tab_registro, base)

    extra_val  = 0
    extra_nome = None
    if extra_info:
        extra_nome = extra_info[0]
        extra_val  = base * extra_info[1]

    total = escritura_val + registro_val + extra_val

    return dict(
        escritura=escritura_val,
        registro=registro_val,
        extra=extra_val,
        extra_nome=extra_nome,
        total=total,
        escritura_faixa=escritura_faixa,
        registro_faixa=registro_faixa,
        aviso=None,
        origem="codigo",
        fonte_nome="Tabela legada do sistema",
        fonte_url="",
        fonte_ano=None,
        fonte_status="legada",
        fonte_vigencia="2025/2026",
        fontes=[],
    )


def tabela_rows_html(tabela, faixa_ativa_idx):
    """Retorna apenas o HTML da tabela (sem wrapper <details>), para uso com st.expander."""
    rows = ""
    for i,(limite, valor) in enumerate(tabela):
        limite_ant = tabela[i-1][0] if i > 0 else 0.0
        if limite == float('inf'):
            faixa_str = f"Acima de R$ {tabela[-2][0]:,.2f}"
        else:
            faixa_str = f"R$ {limite_ant:,.2f} — R$ {limite:,.2f}"
        faixa_str = faixa_str.replace(",","X").replace(".",",").replace("X",".")
        valor_str = f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")
        destaque = ' style="background:#eff6ff;font-weight:700"' if i == faixa_ativa_idx else ""
        badge = ' <span style="font-size:10px;background:#3b82f6;color:#fff;padding:1px 6px;border-radius:99px;margin-left:4px">✓ faixa usada</span>' if i == faixa_ativa_idx else ""
        rows += f"<tr{destaque}><td style='padding:5px 10px;border-bottom:1px solid #e4e4e7'>{faixa_str}</td><td style='padding:5px 10px;border-bottom:1px solid #e4e4e7;text-align:right'>{valor_str}{badge}</td></tr>"
    return f"""<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:4px">
    <tr style="background:#18181b;color:#fff"><th style="padding:6px 10px;text-align:left">Faixa de valor</th><th style="padding:6px 10px;text-align:right">Custo</th></tr>
    {rows}
    </table>"""


def tabela_html(tabela, faixa_ativa_idx, titulo):
    """Mantido para compatibilidade — usa <details> HTML."""
    return f"""<details style="margin-top:8px">
    <summary style="cursor:pointer;font-size:13px;color:#3b82f6;font-weight:600">📋 Ver tabela completa — {titulo}</summary>
    {tabela_rows_html(tabela, faixa_ativa_idx)}
    </details>"""
