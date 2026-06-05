from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from django.views.decorators.http import require_POST
from core.calculos.motor import calcular
from apps.imoveis.models import Imovel
from .models import LancamentoFinanceiro, CategoriaFinanceira
from .forms import LancamentoForm


def _categoria_payload(categoria):
    return {
        "id": str(categoria.pk),
        "nome": categoria.nome,
        "tipo": categoria.tipo,
        "icone": categoria.icone,
        "label": f"{categoria.icone} {categoria.nome}",
        "uso": categoria.lancamentos.count(),
    }


def _form_lancamento_context(request, form, imovel=None, lancamento=None):
    imoveis_payload = [
        {
            "id": str(im.pk),
            "label": im.titulo_card,
            "meta": f"{im.cidade} - {im.estado} · {im.etapa_display}",
        }
        for im in request.user.imoveis.all()
    ]
    categorias_payload = [
        _categoria_payload(categoria)
        for categoria in CategoriaFinanceira.objects.all()
    ]
    return {
        "form": form,
        "imovel": imovel,
        "lancamento": lancamento,
        "imoveis_payload": imoveis_payload,
        "categorias_payload": categorias_payload,
        "selected_imovel_id": str(form["imovel"].value() or ""),
        "selected_categoria_id": str(form["categoria"].value() or ""),
        "selected_tipo": form["tipo"].value() or "despesa",
    }


@login_required
def dashboard(request):
    lancamentos = LancamentoFinanceiro.objects.filter(user=request.user, status="confirmado")
    imoveis = Imovel.objects.filter(user=request.user)

    total_receitas = lancamentos.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or 0
    total_despesas = lancamentos.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or 0
    lucro_liquido = total_receitas - total_despesas

    # KPIs por imóvel (concluídos)
    imoveis_concluidos = imoveis.filter(etapa="concluido")
    operacoes = []
    roi_list = []
    tempo_list = []
    for im in imoveis_concluidos:
        try:
            r = calcular(im.to_calc_dict(), im.giro_padrao)
            operacoes.append({"imovel": im, "resultado": r["resultado"], "roi": r["roi"]})
            roi_list.append(r["roi"])
            tempo_list.append(im.giro_padrao)
        except Exception:
            pass

    roi_medio = sum(roi_list) / len(roi_list) if roi_list else None
    tempo_medio = sum(tempo_list) / len(tempo_list) if tempo_list else None

    # Histórico de lançamentos
    historico = lancamentos.order_by("-data")[:20]

    # Resumo por categoria
    por_categoria = (
        lancamentos.values("categoria__nome", "categoria__icone", "tipo")
        .annotate(total=Sum("valor"))
        .order_by("-total")[:10]
    )

    # Imposto de Renda — gastos tributáveis por imóvel
    # "Gastos tributáveis" são despesas que reduzem a base de cálculo do IR ganho de capital:
    # reformas, ITBI, escritura, registro, comissão leiloeiro, laudêmio (comprovados com nota fiscal)
    ir_por_imovel = []
    for im in imoveis:
        try:
            r = calcular(im.to_calc_dict(), im.giro_padrao)
            # Gastos dedutíveis do IR (custo de aquisição + benfeitorias documentadas)
            gastos_dedutiveis = [
                ("Lance pago",          r["val_inicial"]),
                ("Comissão leiloeiro",  r["com_leil"]),
                ("ITBI",                r["itbi"]),
                ("Escritura",           r["escritura"]),
                ("Registro",            r["registro"]),
                ("Laudêmio",            r["laudemio"]),
                ("Reformas",            r["reformas"]),
            ]
            # Lançamentos financeiros registrados como despesa para este imóvel
            lancs_imovel = lancamentos.filter(imovel=im, tipo="despesa").order_by("-data")
            ir_por_imovel.append({
                "imovel": im,
                "ir_estimado": r["ir"],
                "lucro_bruto": r["lucro_bruto"],
                "preco_venda": r["preco_venda"],
                "gastos_dedutiveis": [(k, v) for k, v in gastos_dedutiveis if v],
                "total_dedutiveis": sum(v for _, v in gastos_dedutiveis if v),
                "lancamentos": lancs_imovel[:5],
                "total_lancamentos": lancs_imovel.count(),
            })
        except Exception:
            pass

    tab_ativa = request.GET.get("tab", "ativas")

    return render(request, "financeiro/dashboard.html", {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "lucro_liquido": lucro_liquido,
        "roi_medio": roi_medio,
        "tempo_medio": tempo_medio,
        "operacoes": operacoes,
        "historico": historico,
        "por_categoria": por_categoria,
        "total_imoveis": imoveis.count(),
        "imoveis_ativos": imoveis.exclude(etapa="concluido").count(),
        "ir_por_imovel": ir_por_imovel,
        "tab_ativa": tab_ativa,
    })


@login_required
def novo_lancamento(request):
    imovel_id = request.GET.get("imovel")
    imovel = None
    if imovel_id:
        imovel = get_object_or_404(Imovel, pk=imovel_id, user=request.user)

    if request.method == "POST":
        form = LancamentoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            l = form.save(commit=False)
            l.user = request.user
            l.save()
            messages.success(request, "✅ Lançamento registrado com sucesso.")
            return redirect("financeiro")
    else:
        initial = {"data": timezone.localdate(), "status": "confirmado", "tipo": "despesa"}
        if imovel:
            initial["imovel"] = imovel
        form = LancamentoForm(user=request.user, initial=initial)

    return render(request, "financeiro/form_lancamento.html", _form_lancamento_context(request, form, imovel=imovel))


@login_required
def editar_lancamento(request, pk):
    l = get_object_or_404(LancamentoFinanceiro, pk=pk, user=request.user)
    if request.method == "POST":
        form = LancamentoForm(request.POST, request.FILES, instance=l, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Lançamento atualizado.")
            return redirect("financeiro")
    else:
        form = LancamentoForm(instance=l, user=request.user)
    return render(request, "financeiro/form_lancamento.html", _form_lancamento_context(request, form, imovel=l.imovel, lancamento=l))


@login_required
@require_POST
def excluir_lancamento(request, pk):
    l = get_object_or_404(LancamentoFinanceiro, pk=pk, user=request.user)
    l.delete()
    messages.success(request, "🗑️ Lançamento excluído.")
    return redirect("financeiro")


@login_required
@require_POST
def criar_categoria(request):
    nome = (request.POST.get("nome") or "").strip()
    tipo = request.POST.get("tipo")
    icone = (request.POST.get("icone") or "💰").strip()[:5] or "💰"
    if tipo not in dict(CategoriaFinanceira.TIPO_CHOICES):
        return JsonResponse({"success": False, "error": "Tipo inválido."}, status=400)
    if not nome:
        return JsonResponse({"success": False, "error": "Informe o nome da categoria."}, status=400)

    categoria = CategoriaFinanceira.objects.create(nome=nome, tipo=tipo, icone=icone)
    return JsonResponse({"success": True, "categoria": _categoria_payload(categoria)}, status=201)


@login_required
@require_POST
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    nome = (request.POST.get("nome") or "").strip()
    tipo = request.POST.get("tipo")
    icone = (request.POST.get("icone") or "💰").strip()[:5] or "💰"
    if tipo not in dict(CategoriaFinanceira.TIPO_CHOICES):
        return JsonResponse({"success": False, "error": "Tipo inválido."}, status=400)
    if not nome:
        return JsonResponse({"success": False, "error": "Informe o nome da categoria."}, status=400)

    categoria.nome = nome
    categoria.tipo = tipo
    categoria.icone = icone
    categoria.save(update_fields=["nome", "tipo", "icone"])
    return JsonResponse({"success": True, "categoria": _categoria_payload(categoria)})


@login_required
@require_POST
def excluir_categoria(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    categoria.delete()
    return JsonResponse({"success": True, "deleted_id": str(pk)})
