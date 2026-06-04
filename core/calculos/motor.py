"""
Motor de cálculo financeiro para leilão de imóveis.
Portado do app.py Streamlit — lógica 100% Python puro, sem dependências de UI.
"""
import math
from .cartorio import calcular_cartorio

GIRO_MESES = [1, 3, 4, 6, 7, 9, 10, 12]


# ── Formatação ─────────────────────────────────────────────────────────────────

def fmt_brl(v, short=False):
    if v is None:
        return "—"
    neg = v < 0
    av = abs(v)
    if short:
        if av >= 1_000_000:
            s = f"R$ {av / 1e6:.1f}M"
        elif av >= 1_000:
            s = f"R$ {av / 1e3:.0f} mil"
        else:
            s = f"R$ {av:.0f}"
    else:
        s = "R$ {:,.2f}".format(av).replace(",", "X").replace(".", ",").replace("X", ".")
    return f"({s})" if neg else s


def fmt_pct(v):
    return f"{v:.2f}%".replace(".", ",")


# ── Motor SAC ──────────────────────────────────────────────────────────────────

def calc_sac(valor_financiado, prazo_meses, cet_aa):
    if valor_financiado <= 0 or prazo_meses <= 0:
        return [], 0
    taxa_am = (1 + cet_aa / 100) ** (1 / 12) - 1
    amortizacao = valor_financiado / prazo_meses
    parcelas = []
    saldo = valor_financiado
    for _ in range(1, prazo_meses + 1):
        juros = saldo * taxa_am
        parcela = amortizacao + juros
        saldo -= amortizacao
        parcelas.append(
            dict(amortizacao=amortizacao, juros=juros, parcela=parcela, saldo=max(saldo, 0))
        )
    return parcelas, taxa_am


def soma_parcelas(parcelas, ate_mes):
    return sum(p["parcela"] for p in parcelas[:ate_mes])


def saldo_devedor_mes(parcelas, mes):
    if not parcelas or mes <= 0:
        return 0
    return parcelas[min(mes - 1, len(parcelas) - 1)]["saldo"]


# ── IR Ganho de Capital ────────────────────────────────────────────────────────

def calc_ir_gc(lucro, tipo):
    if lucro <= 0:
        return 0
    if tipo == "Pessoa Jurídica":
        return lucro * 0.15
    if lucro <= 5_000_000:
        return lucro * 0.15
    elif lucro <= 10_000_000:
        return lucro * 0.175
    elif lucro <= 30_000_000:
        return lucro * 0.20
    else:
        return lucro * 0.225


# ── Custo de oportunidade ──────────────────────────────────────────────────────

def custo_op(capital, meses, rend_aa):
    if rend_aa <= 0 or meses <= 0:
        return 0
    taxa_am = (1 + rend_aa / 100) ** (1 / 12) - 1
    return capital * ((1 + taxa_am) ** meses - 1)


# ── Cálculo principal ──────────────────────────────────────────────────────────

def calcular(p, meses_giro):
    lance = p.get("lance", 0)
    preco_venda_base = p.get("preco_venda", 0)
    taxa_acrescimo = p.get("taxa_acrescimo", 0.0)
    desconto_venda = p.get("desconto_venda", 0.0)
    preco_venda = preco_venda_base * (1 + taxa_acrescimo / 100) * (1 - desconto_venda / 100)
    tipo_pgto = p.get("tipo_pgto", "À Vista")
    entrada = p.get("entrada", 100)
    prazo_fin = p.get("prazo_fin", 240)
    cet_aa = p.get("cet_aa", 10.5)
    pct_leiloeiro = p.get("pct_leiloeiro", 5.0)
    aliq_itbi = p.get("aliq_itbi", 2.0)
    aliq_itbi_fin = p.get("aliq_itbi_fin", 0.0)
    pct_itbi_base = p.get("pct_itbi_base", "Arrematação")
    av_fiscal = p.get("av_fiscal", lance)
    estado = p.get("estado", "BA")
    tipo_leilao = p.get("tipo_leilao", "Extrajudicial")
    modo_cartorio = p.get("modo_cartorio", "Automático")
    escritura_man = p.get("escritura_manual", 0)
    registro_man = p.get("registro_manual", 0)
    reformas = p.get("reformas", 0)
    custo_desocup = p.get("custo_desocup", 0)
    debitos = p.get("debitos", 0)
    despesas_div = p.get("despesas_div", 0)
    laudemio_pct = p.get("laudemio_pct", 0)
    meses_titulo = p.get("meses_titulo", 0)
    iptu_am = p.get("iptu_am", 0)
    cond_am = p.get("cond_am", 0)
    custo_oport_aa = p.get("custo_oport_aa", 0)
    pct_corretor = p.get("pct_corretor", 5.0)
    rec_aluguel_am = p.get("rec_aluguel_am", 0)
    tipo_pessoa = p.get("tipo_pessoa", "Pessoa Física")

    # Financiamento SAC
    if tipo_pgto in ("Financiamento", "Financiamento SAC"):
        val_entrada = lance * entrada / 100
        val_financiado = lance - val_entrada
        parc_sac, _ = calc_sac(val_financiado, prazo_fin, cet_aa)
        val_inicial = val_entrada
        total_parc = soma_parcelas(parc_sac, meses_giro)
        saldo_dev = saldo_devedor_mes(parc_sac, meses_giro)
    else:
        val_entrada = lance
        val_financiado = 0
        parc_sac = []
        val_inicial = lance
        total_parc = 0
        saldo_dev = 0

    # Comissão leiloeiro
    com_leil = lance * pct_leiloeiro / 100

    # ITBI
    base_itbi = av_fiscal if pct_itbi_base == "Avaliação Fiscal" else lance
    if val_financiado > 0:
        itbi = (lance - val_financiado) * aliq_itbi / 100 + val_financiado * (aliq_itbi_fin or aliq_itbi) / 100
    else:
        itbi = base_itbi * aliq_itbi / 100

    # Cartório — base = max(lance, av_fiscal) per TJ-BA e outros
    base_cartorio = max(lance, av_fiscal) if av_fiscal > 0 else lance
    if modo_cartorio == "Automático":
        cart = calcular_cartorio(estado, base_cartorio, tipo_leilao)
        escritura = cart["escritura"]
        registro = cart["registro"]
        extra_cart = cart["extra"]
    else:
        escritura = escritura_man
        registro = registro_man
        extra_cart = 0

    # Financiamento SAC: contrato bancário substitui a escritura pública
    if tipo_pgto in ("Financiamento", "Financiamento SAC"):
        escritura = 0

    # Laudêmio
    laudemio = base_cartorio * laudemio_pct / 100

    # Recorrentes
    meses_ef = max(meses_giro - meses_titulo, 0)
    tot_iptu = iptu_am * meses_ef
    tot_cond = cond_am * meses_ef
    tot_aluguel = rec_aluguel_am * meses_ef

    # Custo de oportunidade
    cap_imob = val_inicial + com_leil + itbi + registro + escritura + reformas + custo_desocup
    cop = custo_op(cap_imob, meses_giro, custo_oport_aa)

    # Corretor na venda
    corretor = preco_venda * pct_corretor / 100

    # IR Ganho de Capital
    custo_aq_ir = lance + com_leil + itbi + registro + escritura + laudemio + reformas
    lucro_bruto = preco_venda - custo_aq_ir - corretor - debitos - despesas_div
    ir = calc_ir_gc(lucro_bruto, tipo_pessoa)

    # Custo total
    custo_total = (
        val_inicial + com_leil + itbi + registro + escritura + laudemio
        + reformas + custo_desocup + debitos + despesas_div
        + tot_iptu + tot_cond + cop
        + total_parc + saldo_dev
        + ir + corretor
        - tot_aluguel
    )

    resultado = preco_venda - custo_total

    cap_roi = val_inicial + com_leil + itbi + registro + escritura + laudemio + reformas + custo_desocup
    roi = (resultado / cap_roi * 100) if cap_roi > 0 else 0
    tem = ((1 + roi / 100) ** (1 / meses_giro) - 1) * 100 if meses_giro > 0 else roi

    # custo_ate_venda = custos de aquisição + posse (sem IR e sem Corretor de venda,
    # pois esses são pagos NO ato da venda/depois, não são custos "até a venda")
    # ROI operacional: resultado ÷ custo_ate_venda
    custo_ate_venda = (
        val_inicial + com_leil + itbi + registro + escritura + laudemio
        + reformas + custo_desocup + debitos + despesas_div
        + tot_iptu + tot_cond + cop
        - tot_aluguel
    )
    roi_custo = (resultado / custo_ate_venda * 100) if custo_ate_venda > 0 else 0
    tem_custo = ((1 + roi_custo / 100) ** (1 / meses_giro) - 1) * 100 if meses_giro > 0 else roi_custo

    return dict(
        lance=lance, preco_venda=preco_venda, preco_venda_base=preco_venda_base,
        meses=meses_giro,
        val_financiado=val_financiado, val_entrada=val_entrada, val_inicial=val_inicial,
        total_parc=total_parc, saldo_dev=saldo_dev,
        com_leil=com_leil, itbi=itbi, escritura=escritura, registro=registro,
        extra_cart=extra_cart, laudemio=laudemio,
        reformas=reformas, custo_desocup=custo_desocup,
        debitos=debitos, despesas_div=despesas_div,
        tot_iptu=tot_iptu, tot_cond=tot_cond, cop=cop,
        corretor=corretor, tot_aluguel=tot_aluguel,
        lucro_bruto=lucro_bruto, ir=ir,
        custo_total=custo_total, custo_ate_venda=custo_ate_venda,
        resultado=resultado,
        roi=roi, tem=tem,
        roi_custo=roi_custo, tem_custo=tem_custo,
    )


def tabela_giro(p):
    return {m: calcular(p, m) for m in GIRO_MESES}


def lance_maximo(p):
    """Estima o lance máximo para atingir o lucro mínimo desejado."""
    lucro_minimo = p.get("lucro_minimo", 0)
    incremento = p.get("incremento_lance", 5000)
    if not lucro_minimo:
        return None
    preco_venda = p.get("preco_venda", 0)
    taxa_acrescimo = p.get("taxa_acrescimo", 0.0)
    desconto_venda = p.get("desconto_venda", 0.0)
    pv_adj = preco_venda * (1 + taxa_acrescimo / 100) * (1 - desconto_venda / 100)
    pct_corretor = p.get("pct_corretor", 5.0)
    pct_leiloeiro = p.get("pct_leiloeiro", 5.0)
    aliq_itbi = p.get("aliq_itbi", 2.0)
    reformas = p.get("reformas", 0)
    custo_desocup = p.get("custo_desocup", 0)
    debitos = p.get("debitos", 0)
    despesas_div = p.get("despesas_div", 0)
    av_fiscal = p.get("av_fiscal", 0)
    estado = p.get("estado", "BA")
    tipo_leilao = p.get("tipo_leilao", "Extrajudicial")
    cart_est = calcular_cartorio(estado, av_fiscal if av_fiscal > 0 else 1, tipo_leilao)
    reg_est = cart_est["registro"]
    corr_v = pv_adj * pct_corretor / 100
    custos_fixos = corr_v + reg_est + reformas + custo_desocup + debitos + despesas_div
    lance_max_bruto = (pv_adj - custos_fixos - lucro_minimo) / (1 + pct_leiloeiro / 100 + aliq_itbi / 100)
    if incremento > 0:
        return math.floor(lance_max_bruto / incremento) * incremento
    return lance_max_bruto


def tabela_lances(p):
    """Gera tabela de lances progressivos com resultados para diferentes períodos.
    
    Args:
        p: Dicionário com parâmetros da simulação
    
    Returns:
        Lista com dicts contendo: lance, lucro_estimado, resultado_por_giro
    """
    lance_inicial = p.get("lance", 300000)
    incremento = p.get("incremento_lance", 5000)
    lucro_minimo = p.get("lucro_minimo", 0)
    
    if incremento <= 0:
        return []
    
    tabela = []
    lance_maximo_val = lance_maximo(p)
    
    # Se não tem lucro mínimo, gera 10 lances progressivos
    # Se tem, gera até o lance máximo
    if not lucro_minimo or not lance_maximo_val:
        limite = lance_inicial + (10 * incremento)
    else:
        limite = min(lance_maximo_val + incremento, lance_inicial + (20 * incremento))
    
    lance = lance_inicial
    while lance <= limite:
        # Atualiza o parâmetro de lance
        p_lance = p.copy()
        p_lance["lance"] = lance
        
        # Gera a tabela de giro para este lance
        tg = tabela_giro(p_lance)
        
        # Extrai resultados para cada período
        resultado_por_giro = {}
        for meses in GIRO_MESES:
            if meses in tg:
                resultado_por_giro[meses] = tg[meses]
        
        tabela.append({
            "lance": lance,
            "resultado_por_giro": resultado_por_giro
        })
        
        lance += incremento
    
    return tabela
