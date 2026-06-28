from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from core.calculos.motor import calcular, tabela_giro, fmt_brl, fmt_pct, GIRO_MESES, lance_maximo, tabela_lances
from core.calculos.cartorio import (
    calcular_cartorio, buscar_faixa, ESTADOS_DISPONIVEIS, ESTADOS_NOMES, TODOS_ESTADOS,
    obter_tabelas_cartorio,
)


def _form_to_params(post):
    def f(k, d=0.0):
        try:
            return float(post.get(k, d))
        except (ValueError, TypeError):
            return float(d)

    def i(k, d=0):
        try:
            return int(float(post.get(k, d)))
        except (ValueError, TypeError):
            return d

    return {
        "lance":           f("lance", 300000),
        "avaliacao":       f("avaliacao", 400000),
        "preco_venda":     f("preco_venda", 420000),
        "taxa_acrescimo":  f("taxa_acrescimo"),
        "desconto_venda":  f("desconto_venda"),
        "tipo_pgto":       post.get("tipo_pgto", "À Vista"),
        "entrada":         f("entrada", 100),
        "prazo_fin":       i("prazo_fin"),
        "cet_aa":          f("cet_aa"),
        "pct_leiloeiro":   f("pct_leiloeiro", 5),
        "aliq_itbi":       f("aliq_itbi", 2),
        "aliq_itbi_fin":   f("aliq_itbi_fin"),
        "pct_itbi_base":   post.get("pct_itbi_base", "Arrematação"),
        "av_fiscal":       f("av_fiscal"),
        "estado":          post.get("estado", "BA"),
        "tipo_leilao":     post.get("tipo_leilao", "Extrajudicial"),
        "modo_cartorio":   post.get("modo_cartorio", "Automático"),
        "escritura_manual":f("escritura_manual"),
        "registro_manual": f("registro_manual"),
        "reformas":        f("reformas"),
        "custo_desocup":   f("custo_desocup"),
        "debitos":         f("debitos"),
        "despesas_div":    f("despesas_div"),
        "laudemio_pct":    f("laudemio_pct"),
        "meses_titulo":    i("meses_titulo"),
        "iptu_am":         f("iptu_am"),
        "cond_am":         f("cond_am"),
        "custo_oport_aa":  f("custo_oport_aa"),
        "tipo_pessoa":     post.get("tipo_pessoa", "Pessoa Física"),
        "pct_corretor":    f("pct_corretor", 5),
        "rec_aluguel_am":  f("rec_aluguel_am"),
        "lucro_minimo":    f("lucro_minimo"),
        "incremento_lance":f("incremento_lance", 5000),
    }


@login_required
def index(request):
    estados = [(uf, f"{uf} — {ESTADOS_NOMES.get(uf, uf)}") for uf in TODOS_ESTADOS]
    return render(request, "calculadora/index.html", {
        "estados": estados,
        "giro_meses": GIRO_MESES,
    })


@login_required
@require_POST
def calcular_htmx(request):
    p = _form_to_params(request.POST)
    tg = tabela_giro(p)
    r12 = tg[12]

    base_cart = max(p["lance"], p["av_fiscal"]) if p["av_fiscal"] > 0 else p["lance"]
    cart = calcular_cartorio(p["estado"], base_cart, p["tipo_leilao"])
    if p["tipo_pgto"] == "Financiamento SAC":
        cart["escritura"] = 0
        cart["total"] = cart["registro"] + (cart.get("extra") or 0)

    tab_esc = tab_reg = idx_esc = idx_reg = None
    tabelas_cartorio = obter_tabelas_cartorio(p["estado"], p["tipo_leilao"])
    if tabelas_cartorio["registro"]:
        if p["tipo_leilao"] == "Extrajudicial" and tabelas_cartorio["escritura"]:
            tab_esc = tabelas_cartorio["escritura"]
            _, _, idx_esc = buscar_faixa(tab_esc, base_cart)
        tab_reg = tabelas_cartorio["registro"]
        _, _, idx_reg = buscar_faixa(tab_reg, base_cart)

    lance_max = lance_maximo(p)
    desconto = (1 - p["lance"] / p["avaliacao"]) * 100 if p["avaliacao"] > 0 else 0

    return render(request, "calculadora/resultado_htmx.html", {
        "p": p,
        "tg": tg,
        "r12": r12,
        "cart": cart,
        "base_cart": base_cart,
        "tab_esc": tab_esc,
        "tab_reg": tab_reg,
        "idx_esc": idx_esc,
        "idx_reg": idx_reg,
        "giro_meses": GIRO_MESES,
        "lance_max": lance_max,
        "desconto": desconto,
        "fmt_brl": fmt_brl,
        "fmt_pct": fmt_pct,
        "estado_nome": ESTADOS_NOMES.get(p["estado"], p["estado"]),
        "estado_disponivel": bool(tabelas_cartorio["registro"]) or p["estado"] in ESTADOS_DISPONIVEIS,
    })

@login_required
@require_POST
def tabela_lances_view(request):
    """Retorna a tabela de lances progressivos em HTML."""
    from django.http import JsonResponse
    p = _form_to_params(request.POST)
    tabela = tabela_lances(p)
    
    # Formata para HTML
    html_rows = []
    for item in tabela:
        lance = item["lance"]
        resultados = item["resultado_por_giro"]
        
        row_html = f'<tr><td class="font-bold text-right">{fmt_brl(lance)}</td>'
        
        for mes in GIRO_MESES:
            if mes in resultados:
                r = resultados[mes]
                roi = r.get("roi", 0)
                resultado = r.get("resultado", 0)
                
                # Cor baseada no ROI
                if roi >= 15:
                    cor_classe = "bg-green-100 text-green-900"
                elif roi > 0:
                    cor_classe = "bg-yellow-100 text-yellow-900"
                else:
                    cor_classe = "bg-red-100 text-red-900"
                
                row_html += f'<td class="{cor_classe} text-right text-sm">{fmt_pct(roi)}</td>'
        
        row_html += '</tr>'
        html_rows.append(row_html)
    
    return JsonResponse({
        "success": True,
        "html": "\n".join(html_rows),
        "giro_meses": GIRO_MESES,
    })
