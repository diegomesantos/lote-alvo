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


# ── Simulador "Morar: Comprar vs. Alugar" ──────────────────────────────────────

def _sac_com_amortizacao_extra(valor_financiado, prazo_meses, cet_aa, extra_am, modo):
    """Gera a tabela SAC aplicando amortização extra mensal.

    modo == "prazo"   → mantém a amortização base, o extra abate saldo e
                        encerra o financiamento antes (parcela cai naturalmente).
    modo == "parcela" → recalcula a amortização base sobre o saldo/prazo restante
                        a cada aporte, reduzindo a parcela mas mantendo o prazo.

    Retorna (parcelas, taxa_am). Cada parcela tem amortizacao, juros, parcela,
    extra, saldo.
    """
    if valor_financiado <= 0 or prazo_meses <= 0:
        return [], 0
    taxa_am = (1 + cet_aa / 100) ** (1 / 12) - 1
    amortizacao_base = valor_financiado / prazo_meses
    parcelas = []
    saldo = valor_financiado
    extra_am = max(extra_am or 0, 0)

    for mes in range(1, prazo_meses + 1):
        if saldo <= 0:
            break
        juros = saldo * taxa_am

        if modo == "parcela" and extra_am > 0:
            # Recalcula amortização base sobre prazo restante a cada mês
            meses_restantes = prazo_meses - mes + 1
            amortizacao = saldo / meses_restantes
        else:
            amortizacao = amortizacao_base

        amortizacao = min(amortizacao, saldo)
        saldo_apos_base = saldo - amortizacao

        extra_aplicado = min(extra_am, saldo_apos_base) if extra_am > 0 else 0
        saldo_apos_base -= extra_aplicado

        parcela = amortizacao + juros + extra_aplicado
        saldo = max(saldo_apos_base, 0)
        parcelas.append(
            dict(
                amortizacao=amortizacao,
                juros=juros,
                parcela=parcela,
                extra=extra_aplicado,
                saldo=saldo,
            )
        )
        if saldo <= 0:
            break

    return parcelas, taxa_am


def simular_moradia(params):
    """Compara continuar alugando vs. comprar financiado para morar.

    Reaproveita a lógica SAC (calc_sac). Retorna resumo + séries amostradas
    anualmente para gráficos. Cálculo puro, sem dependência de UI.
    """
    # valor_imovel = preço efetivamente pago (arremate). É a base do financiamento.
    valor_imovel = float(params.get("valor_imovel", 0) or 0)
    # valor_mercado = quanto o imóvel vale de verdade (avaliação/revenda). Em leilão
    # costuma ser maior que o pago — o desconto vira patrimônio imediato do comprador.
    valor_mercado = float(params.get("valor_mercado", 0) or 0) or valor_imovel
    entrada_pct = float(params.get("entrada_pct", 20) or 0)
    prazo_meses = int(params.get("prazo_meses", 360) or 0)
    cet_aa = float(params.get("cet_aa", 10.5) or 0)

    condominio_am = float(params.get("condominio_am", 0) or 0)
    iptu_am = float(params.get("iptu_am", 0) or 0)
    aluguel_am = float(params.get("aluguel_am", 0) or 0)
    # Custos de aquisição (ITBI, cartório, comissão) — saem do bolso do comprador
    # no ato e NÃO viram patrimônio. É o que cria um break-even realista.
    custos_aquisicao = float(params.get("custos_aquisicao", 0) or 0)

    valorizacao_aa = float(params.get("valorizacao_imovel_aa", 6.0) or 0)
    reajuste_aluguel_aa = float(params.get("reajuste_aluguel_aa", 4.5) or 0)
    rendimento_aa = float(params.get("rendimento_invest_aa", 10.0) or 0)
    # IPTU e condomínio reajustam pela inflação ~ reajuste do aluguel
    reajuste_custos_aa = reajuste_aluguel_aa

    amortizacao_extra_am = float(params.get("amortizacao_extra_am", 0) or 0)
    modo_amortizacao = params.get("modo_amortizacao", "prazo") or "prazo"

    val_entrada = valor_imovel * entrada_pct / 100
    val_financiado = max(valor_imovel - val_entrada, 0)

    # Tabela SAC base (sem amortização extra)
    parcelas_base, taxa_am = calc_sac(val_financiado, prazo_meses, cet_aa)
    # Tabela SAC com amortização extra
    parcelas_amort, _ = _sac_com_amortizacao_extra(
        val_financiado, prazo_meses, cet_aa, amortizacao_extra_am, modo_amortizacao
    )

    def _reajuste(valor_base, mes, taxa_aa):
        anos = (mes - 1) // 12
        return valor_base * ((1 + taxa_aa / 100) ** anos)

    taxa_rend_am = (1 + rendimento_aa / 100) ** (1 / 12) - 1 if rendimento_aa > 0 else 0

    # Quem aluga não desembolsa entrada nem custos de aquisição: investe esse
    # capital todo. Quem compra desembolsa entrada+custos, mas só a entrada vira
    # patrimônio (custos de aquisição são "perdidos"). Daí o break-even real.
    patrimonio_aluguel = val_entrada + custos_aquisicao
    # Excedente que o COMPRADOR investe: quando alugar custa mais que a parcela+posse,
    # o comprador economiza essa diferença e investe (espelho do que o locatário faz).
    investido_comprador = 0.0

    juros_totais = 0.0
    juros_totais_amort = sum(p["juros"] for p in parcelas_amort)
    total_desembolsado_compra = val_entrada + custos_aquisicao
    total_desembolsado_aluguel = 0.0

    serie_meses = []
    serie_saldo = []
    serie_saldo_amort = []
    serie_patrim_compra = []
    serie_patrim_compra_so = []   # só imóvel valorizado − saldo, sem investir excedente
    serie_patrim_aluguel = []
    serie_custo_compra = []
    serie_custo_aluguel = []
    serie_juros_acum = []
    # Série mensal completa para tabela detalhada (transmitida como array de objetos)
    tabela_mensal = []

    break_even_mes = None
    juros_acumulado = 0.0

    # Mês 0 — ato da compra. Quem compra desembolsa entrada + custos de aquisição
    # (espelhado em "prestacao"); quem aluga investe esse mesmo capital de partida.
    tabela_mensal.append({
        "m": 0,
        "prestacao": round(val_entrada + custos_aquisicao, 2),
        "aluguel": 0.0,
        "saldo": round(val_financiado, 2),
        "aporte_fin": 0.0,
        "aporte_alug": round(val_entrada + custos_aquisicao, 2),
        "patrim_fin": round(valor_mercado - val_financiado, 2),
        "patrim_alug": round(val_entrada + custos_aquisicao, 2),
    })

    for mes in range(1, prazo_meses + 1):
        # Parcela base do mês (0 se o financiamento base já acabou — não acontece no base)
        if mes <= len(parcelas_base):
            parcela_mes = parcelas_base[mes - 1]["parcela"]
            juros_mes = parcelas_base[mes - 1]["juros"]
            saldo_base = parcelas_base[mes - 1]["saldo"]
        else:
            parcela_mes = 0.0
            juros_mes = 0.0
            saldo_base = 0.0
        juros_totais += juros_mes
        juros_acumulado += juros_mes

        # Saldo no cenário com amortização extra (já quitado vira 0)
        saldo_amort = parcelas_amort[mes - 1]["saldo"] if mes <= len(parcelas_amort) else 0.0

        cond_mes = _reajuste(condominio_am, mes, reajuste_custos_aa)
        iptu_mes = _reajuste(iptu_am, mes, reajuste_custos_aa)
        custo_compra_mes = parcela_mes + cond_mes + iptu_mes

        aluguel_mes = _reajuste(aluguel_am, mes, reajuste_aluguel_aa)
        custo_aluguel_mes = aluguel_mes

        # diferenca > 0  → comprar custa mais que alugar; o LOCATÁRIO economiza e investe.
        # diferenca < 0  → alugar custa mais; o COMPRADOR economiza e investe.
        diferenca = custo_compra_mes - custo_aluguel_mes
        patrimonio_aluguel = patrimonio_aluguel * (1 + taxa_rend_am) + max(diferenca, 0)
        investido_comprador = investido_comprador * (1 + taxa_rend_am) + max(-diferenca, 0)

        total_desembolsado_compra += custo_compra_mes
        total_desembolsado_aluguel += custo_aluguel_mes + max(-diferenca, 0)

        # Patrimônio de quem compra = valor de MERCADO valorizado − saldo devedor.
        # Parte do valor de mercado (não do pago): o desconto do leilão já é patrimônio.
        valor_imovel_mes = valor_mercado * ((1 + valorizacao_aa / 100) ** (mes / 12))
        # "Só financiando" — imóvel valorizado − saldo, sem investir o excedente (passivo).
        patrimonio_compra_so = valor_imovel_mes - saldo_base
        # "Comprando + investindo excedente" — soma o que o comprador investe quando
        # a parcela+posse é menor que o aluguel (espelho de quem aluga e investe).
        patrimonio_compra = patrimonio_compra_so + investido_comprador

        if break_even_mes is None and patrimonio_compra >= patrimonio_aluguel:
            break_even_mes = mes

        # Tabela mensal: aporte do locatário quando comprar custa mais;
        # aporte do comprador quando alugar custa mais.
        aporte_aluguel_mes = max(diferenca, 0)
        aporte_compra_mes = max(-diferenca, 0)
        tabela_mensal.append({
            "m": mes,
            "prestacao": round(custo_compra_mes, 2),
            "aluguel": round(custo_aluguel_mes, 2),
            "saldo": round(saldo_base, 2),
            "aporte_fin": round(aporte_compra_mes, 2),
            "aporte_alug": round(aporte_aluguel_mes, 2),
            "patrim_fin": round(patrimonio_compra, 2),
            "patrim_alug": round(patrimonio_aluguel, 2),
        })

        # Amostra anual (mês 1, 12, 24, ...) + último mês para gráficos
        if mes == 1 or mes % 12 == 0 or mes == prazo_meses:
            serie_meses.append(mes)
            serie_saldo.append(round(saldo_base, 2))
            serie_saldo_amort.append(round(saldo_amort, 2))
            serie_patrim_compra.append(round(patrimonio_compra, 2))
            serie_patrim_compra_so.append(round(patrimonio_compra_so, 2))
            serie_patrim_aluguel.append(round(patrimonio_aluguel, 2))
            serie_custo_compra.append(round(custo_compra_mes, 2))
            serie_custo_aluguel.append(round(custo_aluguel_mes, 2))
            serie_juros_acum.append(round(juros_acumulado, 2))

    prazo_amort = len(parcelas_amort)
    parcela_inicial = parcelas_base[0]["parcela"] if parcelas_base else 0.0
    custo_compra_inicial = parcela_inicial + condominio_am + iptu_am

    patrim_final_compra = serie_patrim_compra[-1] if serie_patrim_compra else 0
    patrim_final_aluguel = serie_patrim_aluguel[-1] if serie_patrim_aluguel else 0

    # Desconto do leilão = patrimônio que já nasce no ato (valor de mercado − pago)
    ganho_desconto = max(valor_mercado - valor_imovel, 0)

    # Diferença mensal inicial (positiva = comprar custa mais que alugar hoje)
    diff_mensal_inicial = custo_compra_inicial - aluguel_am

    # ── Veredito em linguagem simples ──
    vantagem = patrim_final_compra - patrim_final_aluguel
    if abs(vantagem) < max(patrim_final_aluguel, 1) * 0.05:
        veredito_tipo = "empate"
        veredito_titulo = "Tecnicamente empatado no longo prazo"
        veredito_texto = (
            "Comprar e alugar+investir terminam muito próximos em patrimônio. "
            "A decisão pode pesar mais pelo lado pessoal (estabilidade de morar no próprio "
            "imóvel) do que pelo financeiro."
        )
    elif vantagem > 0:
        veredito_tipo = "compra"
        veredito_titulo = "Comprar este imóvel tende a valer mais a pena"
        quando = (
            f"a partir do mês {break_even_mes} (~{break_even_mes // 12} anos e {break_even_mes % 12} meses)"
            if break_even_mes else "ao longo do período simulado"
        )
        veredito_texto = (
            f"No fim do financiamento, comprar deixa você com cerca de "
            f"{fmt_brl(vantagem)} a mais em patrimônio do que alugar e investir a diferença. "
            f"A compra passa à frente {quando}."
        )
    else:
        veredito_tipo = "aluguel"
        veredito_titulo = "Alugar e investir a diferença tende a render mais"
        if diff_mensal_inicial > 0:
            motivo = (
                f"principalmente porque a parcela + custos mensais ({fmt_brl(custo_compra_inicial)}) "
                f"é maior que o aluguel ({fmt_brl(aluguel_am)}), e essa folga investida cresce."
            )
        else:
            motivo = (
                f"mesmo a parcela + custos ({fmt_brl(custo_compra_inicial)}) sendo menor que o aluguel "
                f"({fmt_brl(aluguel_am)}), o peso vem da entrada de {fmt_brl(val_entrada)} + custos da compra: "
                f"investido desde o início, esse capital rende mais do que a valorização do imóvel."
            )
        veredito_texto = (
            f"No fim do período, alugar e investir o dinheiro que sobra deixa você com cerca de "
            f"{fmt_brl(-vantagem)} a mais em patrimônio do que comprar — {motivo}"
        )

    return dict(
        resumo=dict(
            valor_imovel=round(valor_imovel, 2),
            valor_mercado=round(valor_mercado, 2),
            ganho_desconto=round(ganho_desconto, 2),
            val_entrada=round(val_entrada, 2),
            val_financiado=round(val_financiado, 2),
            custos_aquisicao=round(custos_aquisicao, 2),
            parcela_inicial=round(parcela_inicial, 2),
            custo_mensal_compra_inicial=round(custo_compra_inicial, 2),
            aluguel_inicial=round(aluguel_am, 2),
            diff_mensal_inicial=round(diff_mensal_inicial, 2),
            juros_totais=round(juros_totais, 2),
            juros_totais_com_amortizacao=round(juros_totais_amort, 2),
            economia_juros=round(juros_totais - juros_totais_amort, 2),
            prazo_original_meses=prazo_meses,
            prazo_com_amortizacao_meses=prazo_amort,
            meses_economizados=max(prazo_meses - prazo_amort, 0),
            break_even_mes=break_even_mes,
            patrimonio_final_compra=round(patrim_final_compra, 2),
            patrimonio_final_aluguel=round(patrim_final_aluguel, 2),
            total_desembolsado_compra=round(total_desembolsado_compra, 2),
            total_desembolsado_aluguel=round(total_desembolsado_aluguel, 2),
            vantagem=round(vantagem, 2),
            veredito_tipo=veredito_tipo,
            veredito_titulo=veredito_titulo,
            veredito_texto=veredito_texto,
        ),
        series=dict(
            meses=serie_meses,
            saldo_devedor=serie_saldo,
            saldo_devedor_amortizado=serie_saldo_amort,
            patrimonio_compra=serie_patrim_compra,
            patrimonio_compra_so=serie_patrim_compra_so,
            patrimonio_aluguel=serie_patrim_aluguel,
            custo_mensal_compra=serie_custo_compra,
            custo_mensal_aluguel=serie_custo_aluguel,
            juros_acumulado=serie_juros_acum,
        ),
        tabela=tabela_mensal,
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
