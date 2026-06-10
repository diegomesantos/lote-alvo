from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
from urllib.parse import urlencode
from core.calculos.motor import calcular, tabela_giro, fmt_brl, fmt_pct, GIRO_MESES, tabela_lances, simular_moradia
from core.calculos.cartorio import (
    calcular_cartorio, buscar_faixa, ESTADOS_DISPONIVEIS, ESTADOS_NOMES, TODOS_ESTADOS
)
from apps.leiloes.models import ImovelCaixa
from .models import (
    Imovel, ImovelChecklistItem, ImovelArquivo, ImovelComentario,
    CHECKLIST_PADRAO, ETAPA_CHOICES, ETAPA_COR, ETAPAS_PRE_KEYS, ETAPAS_POS_KEYS, ETAPA_PRE, ETAPA_POS
)
from .forms import ImovelForm, ImovelArquivoForm, ImovelCalculoForm


def _resultado_resumo(imovel, meses=6):
    try:
        r = calcular(imovel.to_calc_dict(), meses)
        return r
    except Exception:
        return None


def _valor_presente(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _fmt_m2(value):
    if not value:
        return None
    try:
        texto = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        texto = texto.rstrip("0").rstrip(",")
        return f"{texto} m²"
    except (TypeError, ValueError):
        return f"{value} m²"


def _fmt_data_hora(data, hora=None):
    if not data:
        return None
    texto = data.strftime("%d/%m/%Y")
    if hora:
        texto = f"{texto}, {hora.strftime('%H:%M')}"
    return texto


def _dict_filtrado(items):
    return [
        {"label": label, "value": value}
        for label, value in items
        if _valor_presente(value)
    ]


def _classe_risco_analise(nivel_risco):
    nivel = (nivel_risco or "").lower()
    if nivel in {"baixo", "baixo risco"}:
        return "ok"
    if nivel in {"medio", "médio", "moderado", "medio risco", "médio risco"}:
        return "warn"
    if nivel in {"alto", "critico", "crítico", "alto risco"}:
        return "bad"
    return "neutral"


def _indicador_financeiro(r):
    if not r:
        return {
            "titulo": "Financeiro",
            "status": "neutral",
            "valor": "Não calculado",
            "texto": "Complete a simulação para enxergar retorno, capital exposto e custo até a venda.",
        }

    resultado = float(r.get("resultado") or 0)
    roi = float(r.get("roi") or 0)
    if resultado > 0 and roi >= 15:
        status = "ok"
        texto = "Retorno acima do alvo usual para uma triagem inicial."
    elif resultado > 0:
        status = "warn"
        texto = "Operação positiva, mas exige validação de preço, prazo e custos."
    else:
        status = "bad"
        texto = "Resultado projetado negativo no giro padrão."
    return {
        "titulo": "Financeiro",
        "status": status,
        "valor": fmt_pct(roi),
        "texto": texto,
    }


def _indicadores_decisao(imovel, imovel_caixa, r, analise_resultado):
    desconto = float(imovel.desconto_pct or 0)
    documentos_ok = bool(imovel_caixa and imovel_caixa.matricula_url and imovel_caixa.edital_url)
    risco = (analise_resultado or {}).get("nivel_risco") or ""
    risco_status = _classe_risco_analise(risco)

    if desconto >= 30:
        contexto_status = "ok"
        contexto_texto = "Desconto relevante sobre a avaliação cadastrada."
    elif desconto > 0:
        contexto_status = "warn"
        contexto_texto = "Desconto existe, mas precisa ser comparado com mercado local."
    else:
        contexto_status = "neutral"
        contexto_texto = "Sem desconto calculado a partir dos dados atuais."

    if documentos_ok:
        docs_status = "ok"
        docs_texto = "Matrícula e edital disponíveis para conferência."
    elif imovel_caixa and (imovel_caixa.matricula_url or imovel_caixa.edital_url):
        docs_status = "warn"
        docs_texto = "Há documento parcial; complete a validação antes da decisão."
    else:
        docs_status = "bad"
        docs_texto = "Documentos essenciais ainda não estão vinculados."

    if imovel_caixa and imovel_caixa.ocupado:
        operacao_status = "warn"
        operacao_texto = "Ocupação indicada nos dados Caixa; estime prazo e custo de desocupação."
    elif imovel.custo_desocup and imovel.custo_desocup > 0:
        operacao_status = "warn"
        operacao_texto = "Há custo de desocupação previsto na simulação."
    else:
        operacao_status = "neutral"
        operacao_texto = "Sem alerta operacional forte nos dados atuais."

    if risco_status == "neutral":
        risco_valor = "Pendente"
        risco_texto = "Gere ou revise a análise jurídica para qualificar riscos documentais."
    else:
        risco_valor = risco.title()
        risco_texto = (analise_resultado or {}).get("resumo_executivo") or "Resumo jurídico disponível."

    return [
        _indicador_financeiro(r),
        {
            "titulo": "Desconto",
            "status": contexto_status,
            "valor": fmt_pct(desconto),
            "texto": contexto_texto,
        },
        {
            "titulo": "Documentos",
            "status": docs_status,
            "valor": "Completo" if documentos_ok else "Pendente",
            "texto": docs_texto,
        },
        {
            "titulo": "Jurídico IA",
            "status": risco_status,
            "valor": risco_valor,
            "texto": risco_texto,
        },
        {
            "titulo": "Operação",
            "status": operacao_status,
            "valor": imovel.etapa_display,
            "texto": operacao_texto,
        },
    ]


def _alertas_relatorio(imovel, imovel_caixa, r, analise_resultado):
    alertas = []
    if r and float(r.get("resultado") or 0) < 0:
        alertas.append({
            "titulo": "Resultado financeiro negativo",
            "texto": "Revise preço de venda, lance máximo, custos recorrentes e prazo de giro.",
            "classe": "bad",
        })
    if imovel_caixa and imovel_caixa.ocupado:
        alertas.append({
            "titulo": "Imóvel possivelmente ocupado",
            "texto": "Inclua prazo, custo de desocupação e risco de resistência na decisão.",
            "classe": "warn",
        })
    if imovel_caixa and imovel_caixa.possui_penhora:
        alertas.append({
            "titulo": "Penhora mencionada",
            "texto": "Valide a matrícula e o edital antes de avançar para habilitação.",
            "classe": "bad",
        })
    if imovel_caixa and imovel_caixa.pendencias:
        alertas.append({
            "titulo": "Pendências informadas",
            "texto": ", ".join(imovel_caixa.pendencias),
            "classe": "bad",
        })
    if imovel_caixa and not imovel_caixa.matricula_url:
        alertas.append({
            "titulo": "Matrícula indisponível",
            "texto": "O relatório fica incompleto sem a leitura da matrícula.",
            "classe": "warn",
        })
    risco = _classe_risco_analise((analise_resultado or {}).get("nivel_risco"))
    if risco == "bad":
        alertas.append({
            "titulo": "Risco jurídico alto",
            "texto": (analise_resultado or {}).get("resumo_executivo") or "A análise IA sinalizou risco elevado.",
            "classe": "bad",
        })
    return alertas


def _garantir_checklist_padrao(imovel, user):
    etapas_existentes = set(
        imovel.checklist_items.values_list("etapa", flat=True).distinct()
    )
    novos = []
    for etapa, itens in CHECKLIST_PADRAO.items():
        if etapa in etapas_existentes:
            continue
        for ordem, texto in enumerate(itens, start=1):
            novos.append(ImovelChecklistItem(
                imovel=imovel,
                etapa=etapa,
                texto=texto,
                ordem=ordem,
                criado_por=user,
            ))
    if novos:
        ImovelChecklistItem.objects.bulk_create(novos)


def _checklist_context(imovel):
    itens = list(imovel.checklist_items.all())
    por_etapa = {}
    for item in itens:
        por_etapa.setdefault(item.etapa, []).append(item)

    grupos = []
    total = concluido = 0
    for etapa, label in ETAPA_CHOICES:
        if etapa == "arquivado":
            continue
        etapa_itens = por_etapa.get(etapa, [])
        etapa_total = len(etapa_itens)
        etapa_concluido = sum(1 for item in etapa_itens if item.concluido)
        total += etapa_total
        concluido += etapa_concluido
        grupos.append({
            "key": etapa,
            "label": label,
            "items": etapa_itens,
            "total": etapa_total,
            "concluido": etapa_concluido,
            "aberto": etapa == imovel.etapa,
        })

    return {
        "grupos": grupos,
        "total": total,
        "concluido": concluido,
        "percentual": round((concluido / total) * 100) if total else 0,
    }


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
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "etapa": imovel.etapa,
                "fase": imovel.fase,
                "label": imovel.etapa_display,
            })
    elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "error": "Etapa inválida."}, status=400)
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
    _garantir_checklist_padrao(imovel, request.user)
    p = imovel.to_calc_dict()
    tg = tabela_giro(p)
    r_padrao = tg.get(imovel.giro_padrao, tg.get(12))
    imovel_caixa = None
    if imovel.caixa_imovel_id:
        imovel_caixa = ImovelCaixa.objects.filter(
            imovel_id_caixa=imovel.caixa_imovel_id,
        ).first()

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

    endereco_query = " ".join(
        parte for parte in [imovel.endereco, imovel.cidade, imovel.estado] if parte
    )
    maps_url = f"https://www.google.com/maps/search/?api=1&{urlencode({'query': endereco_query})}"
    maps_embed_url = f"https://maps.google.com/maps?{urlencode({'q': endereco_query, 'output': 'embed'})}"

    imagem_url = None
    if imovel.foto:
        try:
            # Só usa a foto se o arquivo realmente existe no storage. Imagens
            # enviadas antes do B2 (disco efêmero) têm o campo preenchido mas o
            # objeto sumiu — sem checar, a URL assinada apontaria para um 404.
            if imovel.foto.storage.exists(imovel.foto.name):
                imagem_url = imovel.foto.url
        except (ValueError, OSError):
            imagem_url = None
    if not imagem_url and imovel_caixa:
        imagem_url = reverse("leiloes:imagem", args=[imovel_caixa.imovel_id_caixa])

    detalhe_caixa = (imovel_caixa.detalhes or {}).get("detalhe_caixa") if imovel_caixa else {}
    detalhe_caixa = detalhe_caixa or {}

    # Análise jurídica: prefere a do imóvel Caixa vinculado; fallback para análise local (avulso)
    analise_juridica_caixa = (imovel_caixa.detalhes or {}).get("analise_juridica_ia") if imovel_caixa else {}
    analise_juridica_avulso = imovel.analise_juridica_ia or {}
    analise_juridica = analise_juridica_caixa or analise_juridica_avulso
    analise_juridica = analise_juridica or {}
    analise_resultado = analise_juridica.get("resultado") or {}
    analise_nivel_risco = analise_resultado.get("nivel_risco") or "indeterminado"

    # Indica se análise pode ser gerada localmente (imóvel avulso sem Caixa vinculado)
    tem_arquivos_analise = imovel.arquivos.filter(categoria__in=["matricula", "edital"]).exists()
    pode_gerar_analise_avulso = not imovel_caixa and tem_arquivos_analise

    caixa_url = None
    caixa_detalhe_url = None
    if imovel_caixa:
        caixa_url = imovel_caixa.link_caixa or imovel.link_leilao or "https://www.caixa.gov.br/imoveiscaixa"
        caixa_detalhe_url = reverse("leiloes:detalhe", args=[imovel_caixa.imovel_id_caixa])
    elif imovel.link_leilao:
        caixa_url = imovel.link_leilao

    documentos = []
    if imovel_caixa:
        documentos = [
            {
                "nome": "Matrícula",
                "url": imovel_caixa.matricula_url,
                "descricao": "Registro, titularidade, averbações, ônus e restrições.",
                "disponivel": bool(imovel_caixa.matricula_url),
            },
            {
                "nome": "Edital",
                "url": imovel_caixa.edital_url,
                "descricao": "Condições da oferta, responsabilidades e prazos.",
                "disponivel": bool(imovel_caixa.edital_url),
            },
        ]

    dados_imovel = _dict_filtrado([
        ("Tipo", imovel.get_tipo_imovel_display()),
        ("Quartos", imovel_caixa.quartos if imovel_caixa else None),
        ("Área privativa", _fmt_m2(imovel_caixa.area_util) if imovel_caixa else None),
        ("Área total", _fmt_m2(imovel_caixa.area_total) if imovel_caixa else None),
        ("Área terreno", _fmt_m2(imovel_caixa.area_terreno) if imovel_caixa else None),
        ("Bairro", imovel_caixa.bairro if imovel_caixa else None),
        ("CEP", imovel_caixa.cep if imovel_caixa else None),
        ("Situação", imovel_caixa.situacao if imovel_caixa else None),
        ("Ocupado", "Sim" if imovel_caixa and imovel_caixa.ocupado else "Não" if imovel_caixa else None),
        ("ID Caixa", imovel.caixa_imovel_id),
    ])

    dados_leilao = _dict_filtrado([
        ("Vendedor", "CAIXA" if imovel_caixa else None),
        ("Tipo de leilão", imovel.tipo_leilao),
        ("Modalidade", imovel_caixa.modalidade_venda if imovel_caixa else None),
        ("Data da oferta", _fmt_data_hora(
            imovel_caixa.data_leilao,
            imovel_caixa.hora_leilao,
        ) if imovel_caixa else _fmt_data_hora(imovel.data_leilao)),
        ("Avaliação", fmt_brl(imovel_caixa.valor_avaliacao if imovel_caixa else imovel.avaliacao)),
        ("Lance mínimo", fmt_brl(imovel_caixa.valor_minimo_lance if imovel_caixa else imovel.lance)),
        ("Desconto", fmt_pct(imovel_caixa.percentual_desconto if imovel_caixa else imovel.desconto_pct)),
        ("Matrícula", detalhe_caixa.get("matriculas")),
        ("Comarca", detalhe_caixa.get("comarca")),
        ("Ofício", detalhe_caixa.get("oficio")),
        ("Leiloeiro", detalhe_caixa.get("leiloeiro")),
    ])

    formas = (imovel_caixa.formas_pagamento or {}) if imovel_caixa else {}
    pagamentos = [
        {"label": "À vista", "ok": bool(formas.get("a_vista", True)) if imovel_caixa else imovel.tipo_pgto == "À Vista"},
        {"label": "Financiamento", "ok": imovel_caixa.pode_financiar if imovel_caixa else imovel.tipo_pgto == "Financiamento SAC"},
        {"label": "FGTS", "ok": imovel_caixa.pode_fgts if imovel_caixa else False},
        {"label": "Consórcio", "ok": imovel_caixa.pode_consorcio if imovel_caixa else False},
        {"label": "Parcelamento", "ok": bool(formas.get("parcelado", False)) if imovel_caixa else False},
    ]

    indicadores_decisao = _indicadores_decisao(imovel, imovel_caixa, r_padrao, analise_resultado)
    alertas_relatorio = _alertas_relatorio(imovel, imovel_caixa, r_padrao, analise_resultado)
    checklist_operacional = _checklist_context(imovel)
    arquivos = imovel.arquivos.select_related("enviado_por")
    comentarios = imovel.comentarios.select_related("user")

    export_rows = [
        ("Imóvel", imovel.titulo_card),
        ("Endereço", f"{imovel.endereco}, {imovel.cidade}/{imovel.estado}"),
        ("Etapa", imovel.etapa_display),
        ("Prioridade", imovel.get_prioridade_display()),
        ("Avaliação", fmt_brl(imovel.avaliacao)),
        ("Lance", fmt_brl(imovel.lance)),
        ("Preço de venda", fmt_brl(imovel.preco_venda)),
    ]
    if r_padrao:
        export_rows.extend([
            ("Giro padrão", f"{imovel.giro_padrao} meses"),
            ("Resultado", fmt_brl(r_padrao.get("resultado"))),
            ("Custo até a venda", f"-{fmt_brl(r_padrao.get('custo_ate_venda'))}"),
            ("ROI", fmt_pct(r_padrao.get("roi"))),
            ("Taxa mensal equivalente", fmt_pct(r_padrao.get("tem"))),
        ])

    return render(request, "imoveis/detalhe.html", {
        "imovel": imovel,
        "imovel_caixa": imovel_caixa,
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
        "imagem_url": imagem_url,
        "maps_url": maps_url,
        "maps_embed_url": maps_embed_url,
        "caixa_url": caixa_url,
        "caixa_detalhe_url": caixa_detalhe_url,
        "documentos": documentos,
        "dados_imovel": dados_imovel,
        "dados_leilao": dados_leilao,
        "pagamentos": pagamentos,
        "detalhe_caixa": detalhe_caixa,
        "analise_juridica": analise_juridica,
        "analise_resultado": analise_resultado,
        "analise_nivel_risco": analise_nivel_risco,
        "analise_risco_status": _classe_risco_analise(analise_nivel_risco),
        "pode_gerar_analise_avulso": pode_gerar_analise_avulso,
        "analise_juridica_avulso": analise_juridica_avulso,
        "tem_arquivos_analise": tem_arquivos_analise,
        "indicadores_decisao": indicadores_decisao,
        "alertas_relatorio": alertas_relatorio,
        "checklist_operacional": checklist_operacional,
        "arquivos": arquivos,
        "arquivo_form": ImovelArquivoForm(),
        "calculo_form": ImovelCalculoForm(instance=imovel),
        "comentarios": comentarios,
        "export_rows": export_rows,
    })


@login_required
@require_POST
def atualizar_dados_calculo(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    form = ImovelCalculoForm(request.POST, instance=imovel)
    destino = f"{reverse('detalhe', args=[imovel.pk])}#financeiro"
    if form.is_valid():
        form.save()
        messages.success(request, "Dados de cálculo atualizados e relatório recalculado.")
        return redirect(destino)

    messages.error(request, "Não foi possível salvar os dados de cálculo. Revise os campos destacados.")
    return redirect(destino)


@login_required
def criar(request):
    if request.method == "POST":
        form = ImovelForm(request.POST, request.FILES)
        if form.is_valid():
            imovel = form.save(commit=False)
            imovel.user = request.user
            imovel.save()
            _garantir_checklist_padrao(imovel, request.user)
            messages.success(request, f"✅ {imovel.endereco} cadastrado com sucesso!")
            return redirect("detalhe", pk=imovel.pk)
    else:
        form = ImovelForm()
    return render(request, "imoveis/form.html", {"form": form, "titulo": "Novo Imóvel", "novo": True})


@login_required
def editar(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    if request.method == "POST":
        form = ImovelForm(request.POST, request.FILES, instance=imovel)
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
@require_POST
def atualizar_identidade(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    imovel.titulo_personalizado = request.POST.get("titulo_personalizado", "").strip()[:160]
    update_fields = ["titulo_personalizado", "updated_at"]
    if request.FILES.get("foto"):
        imovel.foto = request.FILES["foto"]
        update_fields.append("foto")
    imovel.save(update_fields=update_fields)
    messages.success(request, "Dados do card atualizados.")
    return redirect(f"{reverse('detalhe', args=[imovel.pk])}#resumo")


@login_required
@require_POST
def toggle_checklist_item(request, pk, item_id):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    item = get_object_or_404(ImovelChecklistItem, pk=item_id, imovel=imovel)
    checked = request.POST.get("concluido")
    if checked is None:
        item.concluido = not item.concluido
    else:
        item.concluido = checked in {"1", "true", "True", "on", "sim"}
    item.save(update_fields=["concluido", "atualizado_em"])

    etapa_items = imovel.checklist_items.filter(etapa=item.etapa)
    etapa_total = etapa_items.count()
    etapa_concluido = etapa_items.filter(concluido=True).count()
    geral = _checklist_context(imovel)
    return JsonResponse({
        "success": True,
        "item_id": item.id,
        "concluido": item.concluido,
        "etapa": item.etapa,
        "etapa_total": etapa_total,
        "etapa_concluido": etapa_concluido,
        "total": geral["total"],
        "total_concluido": geral["concluido"],
        "percentual": geral["percentual"],
    })


@login_required
@require_POST
def adicionar_checklist_item(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    etapa = request.POST.get("etapa")
    texto = request.POST.get("texto", "").strip()
    if etapa not in dict(ETAPA_CHOICES) or etapa == "arquivado":
        messages.error(request, "Etapa inválida para o checklist.")
        return redirect(f"{reverse('detalhe', args=[imovel.pk])}#checklist")
    if not texto:
        messages.error(request, "Informe o texto do item.")
        return redirect(f"{reverse('detalhe', args=[imovel.pk])}#checklist")

    ultima_ordem = (
        imovel.checklist_items.filter(etapa=etapa)
        .order_by("-ordem")
        .values_list("ordem", flat=True)
        .first()
        or 0
    )
    ImovelChecklistItem.objects.create(
        imovel=imovel,
        etapa=etapa,
        texto=texto[:320],
        ordem=ultima_ordem + 1,
        criado_por=request.user,
    )
    messages.success(request, "Item adicionado ao checklist.")
    return redirect(f"{reverse('detalhe', args=[imovel.pk])}#checklist")


@login_required
@require_POST
def adicionar_arquivo(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    form = ImovelArquivoForm(request.POST, request.FILES)
    if form.is_valid():
        arquivo = form.save(commit=False)
        arquivo.imovel = imovel
        arquivo.enviado_por = request.user
        arquivo.save()
        messages.success(request, "Arquivo adicionado.")
    else:
        messages.error(request, "Não foi possível adicionar o arquivo.")
    return redirect(f"{reverse('detalhe', args=[imovel.pk])}#arquivos")


@login_required
@require_POST
def excluir_arquivo(request, pk, arquivo_id):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    arquivo = get_object_or_404(ImovelArquivo, pk=arquivo_id, imovel=imovel)
    arquivo.arquivo.delete(save=False)
    arquivo.delete()
    messages.success(request, "Arquivo excluído.")
    return redirect(f"{reverse('detalhe', args=[imovel.pk])}#arquivos")


@login_required
@require_POST
def adicionar_comentario(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    texto = request.POST.get("texto", "").strip()
    if not texto:
        messages.error(request, "Escreva um comentário antes de enviar.")
        return redirect(f"{reverse('detalhe', args=[imovel.pk])}#comentarios")
    ImovelComentario.objects.create(
        imovel=imovel,
        user=request.user,
        texto=texto,
    )
    messages.success(request, "Comentário adicionado.")
    return redirect(f"{reverse('detalhe', args=[imovel.pk])}#comentarios")

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


def _float_post(request, nome, default=0.0):
    """Lê um valor numérico do request (GET ou POST), tolerante a vírgula/vazio."""
    bruto = request.POST.get(nome, request.GET.get(nome))
    if bruto in (None, ""):
        return default
    try:
        return float(str(bruto).replace(".", "").replace(",", ".")) if "," in str(bruto) else float(bruto)
    except (TypeError, ValueError):
        return default


@login_required
def simular_moradia_imovel(request, pk):
    """Simula comprar financiado vs. continuar alugando para um imóvel.

    Pré-preenche com os dados de financiamento do imóvel e aceita overrides
    do usuário. Retorna JSON com resumo + séries para os gráficos.
    """
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)

    # Defaults vindos do imóvel
    # valor_imovel = preço pago (lance/arremate); valor_mercado = avaliação/revenda
    valor_imovel_default = float(imovel.lance or imovel.avaliacao or 0)
    valor_mercado_default = float(
        imovel.preco_venda or imovel.avaliacao or imovel.lance or 0
    )
    # Entrada de 100% = à vista (sem financiamento). Para simular moradia
    # financiada, usar 20% como padrão quando o imóvel não tem financiamento.
    entrada_imovel = float(imovel.entrada or 0)
    entrada_default = entrada_imovel if 0 < entrada_imovel < 100 else 20.0
    prazo_default = int(imovel.prazo_fin or 360)
    cet_default = float(imovel.cet_aa or 10.5)
    cond_default = float(imovel.cond_am or 0)
    iptu_default = float(imovel.iptu_am or 0)

    # Custos de aquisição (ITBI + cartório + comissão) já calculados pelo motor
    try:
        r = calcular(imovel.to_calc_dict(), imovel.giro_padrao or 12)
        custos_aquisicao_default = float(
            (r.get("com_leil") or 0)
            + (r.get("itbi") or 0)
            + (r.get("registro") or 0)
            + (r.get("escritura") or 0)
            + (r.get("extra_cart") or 0)
        )
    except Exception:
        custos_aquisicao_default = 0.0

    params = {
        "valor_imovel": _float_post(request, "valor_imovel", valor_imovel_default),
        "valor_mercado": _float_post(request, "valor_mercado", valor_mercado_default),
        "entrada_pct": _float_post(request, "entrada_pct", entrada_default),
        "prazo_meses": int(_float_post(request, "prazo_meses", prazo_default)),
        "cet_aa": _float_post(request, "cet_aa", cet_default),
        "condominio_am": _float_post(request, "condominio_am", cond_default),
        "iptu_am": _float_post(request, "iptu_am", iptu_default),
        "aluguel_am": _float_post(request, "aluguel_am", 0),
        "custos_aquisicao": _float_post(request, "custos_aquisicao", custos_aquisicao_default),
        "valorizacao_imovel_aa": _float_post(request, "valorizacao_imovel_aa", 6.0),
        "reajuste_aluguel_aa": _float_post(request, "reajuste_aluguel_aa", 4.5),
        "rendimento_invest_aa": _float_post(request, "rendimento_invest_aa", 10.0),
        "amortizacao_extra_am": _float_post(request, "amortizacao_extra_am", 0),
        "modo_amortizacao": request.POST.get("modo_amortizacao", request.GET.get("modo_amortizacao", "prazo")),
    }

    resultado = simular_moradia(params)
    resultado["params"] = params
    return JsonResponse(resultado)


def _payload_analise_processando_avulso(task_id=""):
    from django.conf import settings
    from django.utils import timezone

    agora = timezone.now()
    return {
        "status": "processando",
        "mensagem": (
            "A análise jurídica IA está em processamento. "
            "Você pode permanecer nesta página ou voltar depois."
        ),
        "erro": "",
        "provider": getattr(settings, "AI_LEGAL_ANALYSIS_PROVIDER", "openai"),
        "modelo": getattr(settings, "AI_LEGAL_ANALYSIS_MODEL", ""),
        "task_id": task_id,
        "fontes": [],
        "resultado": None,
        "gerado_em": agora.isoformat(),
        "gerado_em_display": timezone.localtime(agora).strftime("%d/%m/%Y %H:%M"),
    }


@login_required
@require_POST
def gerar_analise_juridica_imovel(request, pk):
    import logging as _logging
    from apps.leiloes.tasks import gerar_analise_juridica_imovel_task

    _logger = _logging.getLogger(__name__)
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)

    analise_atual = imovel.analise_juridica_ia or {}
    if analise_atual.get("status") == "processando":
        messages.info(request, "A análise jurídica IA já está em processamento.")
        return redirect(reverse("detalhe", args=[imovel.pk]) + "#juridico")

    task_id = ""
    imovel.analise_juridica_ia = _payload_analise_processando_avulso()
    imovel.save(update_fields=["analise_juridica_ia", "updated_at"])

    try:
        async_result = gerar_analise_juridica_imovel_task.delay(str(imovel.pk))
        task_id = async_result.id or ""
        imovel.refresh_from_db()
        analise_enfileirada = imovel.analise_juridica_ia or {}
        if analise_enfileirada.get("status") == "processando":
            analise_enfileirada["task_id"] = task_id
            imovel.analise_juridica_ia = analise_enfileirada
            imovel.save(update_fields=["analise_juridica_ia", "updated_at"])
        messages.info(request, "Análise jurídica IA iniciada. A página será atualizada quando terminar.")
    except Exception as exc:
        _logger.exception("Falha ao enfileirar analise juridica IA do imovel avulso %s", imovel.pk)
        imovel.analise_juridica_ia = {
            **_payload_analise_processando_avulso(task_id=task_id),
            "status": "erro",
            "mensagem": "Não foi possível iniciar a análise jurídica IA.",
            "erro": str(exc)[:500],
        }
        imovel.save(update_fields=["analise_juridica_ia", "updated_at"])
        messages.error(request, "Não foi possível iniciar a análise jurídica IA.")

    return redirect(reverse("detalhe", args=[imovel.pk]) + "#juridico")


@login_required
def analise_juridica_imovel_status(request, pk):
    imovel = get_object_or_404(Imovel, pk=pk, user=request.user)
    analise = imovel.analise_juridica_ia or {}
    return JsonResponse({
        "status": analise.get("status") or "nao_iniciada",
        "mensagem": analise.get("mensagem") or "",
        "erro": analise.get("erro") or "",
        "provider": analise.get("provider") or "",
        "modelo": analise.get("modelo") or "",
        "gerado_em_display": analise.get("gerado_em_display") or "",
        "detail_url": reverse("detalhe", args=[imovel.pk]),
    })
