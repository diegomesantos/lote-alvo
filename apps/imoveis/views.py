from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from core.calculos.motor import calcular, tabela_giro, fmt_brl, fmt_pct, GIRO_MESES, tabela_lances
from core.calculos.cartorio import (
    calcular_cartorio, buscar_faixa, ESTADOS_DISPONIVEIS, ESTADOS_NOMES, TODOS_ESTADOS
)
from .models import (
    Imovel, ETAPA_CHOICES, ETAPA_COR, ETAPAS_PRE_KEYS, ETAPAS_POS_KEYS, ETAPA_PRE, ETAPA_POS
)
from .forms import ImovelForm


def _resultado_resumo(imovel, meses=6):
    try:
        r = calcular(imovel.to_calc_dict(), meses)
        return r
    except Exception:
        return None


@login_required
def kanban(request):
    imoveis = Imovel.objects.filter(user=request.user).exclude(etapa="arquivado")
    busca = request.GET.get("q", "").strip()
    aba = request.GET.get("aba", "pre")  # "pre", "pos", ou "financeiro"

    if busca:
        imoveis = imoveis.filter(endereco__icontains=busca) | imoveis.filter(cidade__icontains=busca)

    # Separar por pipeline
    imoveis_pre = imoveis.filter(etapa__in=ETAPAS_PRE_KEYS)
    imoveis_pos = imoveis.filter(etapa__in=ETAPAS_POS_KEYS)

    # Montar colunas para cada pipeline
    def _montar_pipeline(etapas_keys, etapas_labels):
        colunas = []
        for key, label in etapas_labels:
            if key not in etapas_keys:
                continue
            grupo = [im for im in imoveis if im.etapa == key]
            cards = []
            for im in grupo:
                r = _resultado_resumo(im, im.giro_padrao)
                cards.append({"imovel": im, "resultado": r})
            colunas.append({
                "key": key, "label": label, "cor": ETAPA_COR[key], "cards": cards,
                "count": len(cards)
            })
        return colunas

    colunas_pre = _montar_pipeline(ETAPAS_PRE_KEYS, ETAPA_PRE)
    colunas_pos = _montar_pipeline(ETAPAS_POS_KEYS, ETAPA_POS)

    # Contar imóveis por etapa
    totais = {}
    for key, _ in ETAPA_CHOICES:
        if key != "arquivado":
            totais[key] = Imovel.objects.filter(user=request.user, etapa=key).count()

    return render(request, "imoveis/kanban.html", {
        "aba": aba,
        "colunas_pre": colunas_pre,
        "colunas_pos": colunas_pos,
        "totais": totais,
        "busca": busca,
        "total_pre": imoveis_pre.count(),
        "total_pos": imoveis_pos.count(),
        "total_geral": imoveis.count(),
    })


@login_required
@require_POST
def atualizar_etapa(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    nova_etapa = request.POST.get("etapa")
    if nova_etapa in dict(ETAPA_CHOICES):
        imovel.etapa = nova_etapa
        imovel.save(update_fields=["etapa"])
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204)
    return redirect("kanban")


@login_required
def listar(request):
    imoveis = Imovel.objects.filter(user=request.user)
    cards = []
    for im in imoveis:
        r = _resultado_resumo(im, im.giro_padrao)
        cards.append({"imovel": im, "resultado": r})
    return render(request, "imoveis/lista.html", {"cards": cards})


@login_required
def detalhe(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    p = imovel.to_calc_dict()
    tg = tabela_giro(p)
    r_padrao = tg.get(imovel.giro_padrao, tg.get(12))

    base_cart = max(float(imovel.lance), float(imovel.av_fiscal)) if imovel.av_fiscal > 0 else float(imovel.lance)
    cart = calcular_cartorio(imovel.estado, base_cart, imovel.tipo_leilao)
    if imovel.tipo_pgto == "Financiamento SAC":
        cart["escritura"] = 0
        cart["total"] = cart["registro"] + (cart["extra"] or 0)

    tab_esc = tab_reg = idx_esc = idx_reg = None
    if imovel.estado in ESTADOS_DISPONIVEIS:
        dados_est = ESTADOS_DISPONIVEIS[imovel.estado]
        if imovel.tipo_leilao == "Extrajudicial":
            tab_esc = dados_est["escritura"]
            _, _, idx_esc = buscar_faixa(tab_esc, base_cart)
        tab_reg = dados_est["registro"]
        _, _, idx_reg = buscar_faixa(tab_reg, base_cart)

    return render(request, "imoveis/detalhe.html", {
        "imovel": imovel,
        "tg": tg,
        "r_padrao": r_padrao,
        "cart": cart,
        "base_cart": base_cart,
        "tab_esc": tab_esc,
        "tab_reg": tab_reg,
        "idx_esc": idx_esc,
        "idx_reg": idx_reg,
        "giro_meses": GIRO_MESES,
        "etapas": ETAPA_CHOICES,
        "fmt_brl": fmt_brl,
        "fmt_pct": fmt_pct,
    })


@login_required
def criar(request):
    if request.method == "POST":
        form = ImovelForm(request.POST)
        if form.is_valid():
            imovel = form.save(commit=False)
            imovel.user = request.user
            imovel.save()
            messages.success(request, f"✅ {imovel.endereco} cadastrado com sucesso!")
            return redirect("detalhe", pk=imovel.pk)
    else:
        form = ImovelForm()
    return render(request, "imoveis/form.html", {"form": form, "titulo": "Novo Imóvel", "novo": True})


@login_required
def editar(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    if request.method == "POST":
        form = ImovelForm(request.POST, instance=imovel)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ {imovel.endereco} atualizado.")
            return redirect("detalhe", pk=imovel.pk)
    else:
        form = ImovelForm(instance=imovel)
    return render(request, "imoveis/form.html", {"form": form, "titulo": "Editar Imóvel", "imovel": imovel})


@login_required
@require_POST
def excluir(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    nome = imovel.endereco
    imovel.delete()
    messages.success(request, f"🗑️ {nome} excluído.")
    return redirect("kanban")

@login_required
def tabela_lances_imovel(request, pk):
    """Retorna tabela de lances progressivos para um imóvel específico."""
    from django.http import JsonResponse
    
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    p = imovel.to_calc_dict()
    
    tabela = tabela_lances(p)
    
    # Formata para HTML
    html_rows = []
    for item in tabela:
        lance = item["lance"]
        resultados = item["resultado_por_giro"]
        
        row_html = f'<tr><td class="font-bold text-right pr-4">{fmt_brl(lance)}</td>'
        
        for mes in GIRO_MESES:
            if mes in resultados:
                r = resultados[mes]
                roi = r.get("roi", 0)
                
                # Cor baseada no ROI
                if roi >= 15:
                    cor_classe = "bg-green-100 text-green-900"
                elif roi > 0:
                    cor_classe = "bg-yellow-100 text-yellow-900"
                else:
                    cor_classe = "bg-red-100 text-red-900"
                
                row_html += f'<td class="{cor_classe} text-right text-sm p-2">{fmt_pct(roi)}</td>'
        
        row_html += '</tr>'
        html_rows.append(row_html)
    
    return JsonResponse({
        "success": True,
        "html": "\n".join(html_rows),
        "giro_meses": GIRO_MESES,
        "imovel_endereco": imovel.endereco,
    })
