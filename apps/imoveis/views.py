from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlencode
from core.calculos.motor import calcular, tabela_giro, fmt_brl, fmt_pct, GIRO_MESES, tabela_lances, simular_moradia
from core.calculos.cartorio import (
    calcular_cartorio, buscar_faixa, ESTADOS_DISPONIVEIS, ESTADOS_NOMES, TODOS_ESTADOS,
    obter_tabelas_cartorio,
)
from apps.leiloes.models import CAIXA_FOTOS_BASE_URL, ImovelCaixa
from .models import (
    Imovel, ImovelChecklistItem, ImovelArquivo, ImovelComentario, ImovelCompartilhamento,
    NotificacaoUsuario, ChatImovel, ChatMensagem,
    ARQUIVAMENTO_MOTIVO_CHOICES, CHECKLIST_PADRAO, ETAPA_CHOICES, ETAPA_COR,
    ETAPAS_PRE_KEYS, ETAPAS_POS_KEYS, ETAPA_PRE, ETAPA_POS,
    COMPARTILHAMENTO_PERMISSAO_CHOICES
)
from .forms import ImovelForm, ImovelArquivoForm, ImovelCalculoForm


PERMISSAO_LEITURA = "leitura"
PERMISSAO_EDICAO = "edicao"


def _imoveis_acessiveis_queryset(user):
    return (
        Imovel.objects
        .filter(Q(user=user) | Q(compartilhamentos__user=user, compartilhamentos__ativo=True))
        .select_related("user")
        .distinct()
    )


def _imoveis_compartilhados_queryset(user):
    return (
        Imovel.objects
        .filter(compartilhamentos__user=user, compartilhamentos__ativo=True)
        .select_related("user")
        .distinct()
    )


def _imovel_query_por_acesso(user, *, escrita=False, proprietario=False):
    queryset = Imovel.objects.select_related("user")
    if proprietario:
        return queryset.filter(user=user)
    if escrita:
        return queryset.filter(
            Q(user=user)
            | Q(compartilhamentos__user=user, compartilhamentos__ativo=True, compartilhamentos__permissao=PERMISSAO_EDICAO)
        ).distinct()
    return queryset.filter(
        Q(user=user) | Q(compartilhamentos__user=user, compartilhamentos__ativo=True)
    ).distinct()


def _get_imovel_com_acesso(pk, user, *, escrita=False, proprietario=False):
    return get_object_or_404(
        _imovel_query_por_acesso(user, escrita=escrita, proprietario=proprietario),
        pk=pk,
    )


def _acesso_context(imovel, user):
    if imovel.user_id == user.id:
        return {
            "is_owner": True,
            "is_shared": False,
            "can_edit": True,
            "can_manage_shares": True,
            "permissao": "proprietario",
            "permissao_label": "Proprietário",
        }

    compartilhamento = (
        ImovelCompartilhamento.objects
        .filter(imovel=imovel, user=user, ativo=True)
        .select_related("criado_por")
        .first()
    )
    permissao = compartilhamento.permissao if compartilhamento else ""
    return {
        "is_owner": False,
        "is_shared": bool(compartilhamento),
        "can_edit": permissao == PERMISSAO_EDICAO,
        "can_manage_shares": False,
        "permissao": permissao,
        "permissao_label": compartilhamento.permissao_label if compartilhamento else "",
    }


def _nome_usuario(user):
    return user.get_full_name() or user.email or user.username


def _usuario_compartilhamento_payload(user):
    nome = user.get_full_name().strip() or user.username
    email = user.email or ""
    iniciais_base = nome if nome else user.username
    iniciais = "".join(parte[:1] for parte in iniciais_base.split()[:2]).upper() or user.username[:1].upper()
    return {
        "id": user.pk,
        "label": nome,
        "username": user.username,
        "email": email,
        "meta": f"@{user.username}" + (f" · {email}" if email else ""),
        "initials": iniciais[:2],
    }


@login_required
@require_GET
def buscar_usuarios_compartilhamento(request):
    termo_original = request.GET.get("q", "").strip()
    termo = termo_original[1:].strip() if termo_original.startswith("@") else termo_original
    usuarios = User.objects.filter(is_active=True).exclude(pk=request.user.pk)

    if termo:
        for token in termo.split():
            usuarios = usuarios.filter(
                Q(username__icontains=token)
                | Q(email__icontains=token)
                | Q(first_name__icontains=token)
                | Q(last_name__icontains=token)
            )
    elif termo_original != "@":
        return JsonResponse({"results": []})

    usuarios = usuarios.order_by("first_name", "last_name", "username").only(
        "id", "username", "email", "first_name", "last_name"
    )[:20]
    return JsonResponse({
        "results": [_usuario_compartilhamento_payload(usuario) for usuario in usuarios]
    })


def _criar_notificacao_compartilhamento(compartilhamento, *, criado):
    imovel = compartilhamento.imovel
    autor = compartilhamento.criado_por
    autor_nome = _nome_usuario(autor) if autor else "Um usuário"
    titulo = "Imóvel compartilhado com você" if criado else "Acesso ao imóvel atualizado"
    mensagem = (
        f"{autor_nome} compartilhou o imóvel {imovel.titulo_card} com permissão "
        f"{compartilhamento.permissao_label.lower()}."
    )
    if not criado:
        mensagem = (
            f"{autor_nome} atualizou seu acesso ao imóvel {imovel.titulo_card} para "
            f"{compartilhamento.permissao_label.lower()}."
        )

    NotificacaoUsuario.objects.create(
        user=compartilhamento.user,
        tipo="compartilhamento",
        titulo=titulo,
        mensagem=mensagem,
        url=reverse("detalhe", args=[imovel.pk]),
        imovel=imovel,
        criado_por=autor,
    )


def _resultado_resumo(imovel, meses=6):
    try:
        r = calcular(imovel.to_calc_dict(), meses)
        return r
    except Exception:
        return None


def _foto_caixa_url(imovel_id_caixa, sufixo):
    return f"{CAIXA_FOTOS_BASE_URL}/F{imovel_id_caixa}{sufixo}.jpg"


def _foto_upload_url(imovel):
    if not imovel.foto:
        return None
    try:
        if imovel.foto.storage.exists(imovel.foto.name):
            return imovel.foto.url
    except (ValueError, OSError):
        return None
    return None


def _imagem_card_url(imovel, caixa_ids_validos=None):
    """URL da imagem do imóvel para exibir no card/detalhe, ou None.

    Usa a foto enviada (se o arquivo existir no storage); senão, cai na foto
    da Caixa quando o imóvel está vinculado. caixa_ids_validos: set opcional de
    imovel_id_caixa que existem — evita query por card no kanban.
    """
    upload_url = _foto_upload_url(imovel)
    if upload_url:
        return upload_url
    cid = imovel.caixa_imovel_id
    if cid and (caixa_ids_validos is None or cid in caixa_ids_validos):
        return _foto_caixa_url(cid, "21")
    return None


def _imagem_card_fallback_url(imovel, caixa_ids_validos=None):
    if _foto_upload_url(imovel):
        return ""
    cid = imovel.caixa_imovel_id
    if cid and (caixa_ids_validos is None or cid in caixa_ids_validos):
        return _foto_caixa_url(cid, "22")
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


def _documentos_context(imovel, imovel_caixa):
    uploads = {
        arquivo.categoria: arquivo
        for arquivo in imovel.arquivos.filter(categoria__in=["matricula", "edital"]).order_by("-criado_em")
        if arquivo.arquivo
    }

    def montar_documento(nome, categoria, descricao, url_oficial=""):
        upload = uploads.get(categoria)
        if url_oficial:
            return {
                "nome": nome,
                "url": url_oficial,
                "descricao": descricao,
                "disponivel": True,
                "origem": "Caixa",
            }
        if upload:
            return {
                "nome": nome,
                "url": upload.arquivo.url,
                "descricao": descricao,
                "disponivel": True,
                "origem": "Arquivo anexado",
            }
        return {
            "nome": nome,
            "url": "",
            "descricao": descricao,
            "disponivel": False,
            "origem": "",
        }

    documentos = [
        montar_documento(
            "Matrícula",
            "matricula",
            "Registro, titularidade, averbações, ônus e restrições.",
            imovel_caixa.matricula_url if imovel_caixa else "",
        ),
        montar_documento(
            "Edital",
            "edital",
            "Condições da oferta, responsabilidades e prazos.",
            imovel_caixa.edital_url if imovel_caixa else "",
        ),
    ]

    documentos_ok = all(documento["disponivel"] for documento in documentos)
    documentos_parciais = any(documento["disponivel"] for documento in documentos) and not documentos_ok

    # A análise IA usa qualquer documento extraível (PDF ou imagem via OCR),
    # não só matrícula/edital — habilita o botão se houver qualquer anexo válido.
    extensoes_analise = (
        ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif",
    )
    tem_uploads_analise = any(
        arquivo.arquivo and arquivo.arquivo.name.lower().endswith(extensoes_analise)
        for arquivo in imovel.arquivos.all()
    )
    # Imóvel vinculado à Caixa também tem documentos analisáveis (matrícula/edital)
    tem_docs_caixa = bool(imovel_caixa and (imovel_caixa.matricula_url or imovel_caixa.edital_url))
    tem_arquivos_analise = tem_uploads_analise or tem_docs_caixa

    return {
        "documentos": documentos,
        "documentos_ok": documentos_ok,
        "documentos_parciais": documentos_parciais,
        "tem_arquivos_analise": tem_arquivos_analise,
    }


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


def _indicadores_decisao(imovel, imovel_caixa, r, analise_resultado, documentos_context):
    desconto = float(imovel.desconto_pct or 0)
    documentos_ok = documentos_context["documentos_ok"]
    documentos_parciais = documentos_context["documentos_parciais"]
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
    elif documentos_parciais:
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


def _etapas_menu_context():
    return [
        {
            "grupo": "Pré-Arrematação",
            "opcoes": [
                {"key": key, "label": label, "fase": "pre"}
                for key, label in ETAPA_PRE
            ],
        },
        {
            "grupo": "Pós-Arrematação",
            "opcoes": [
                {"key": key, "label": label, "fase": "pos"}
                for key, label in ETAPA_POS
            ],
        },
    ]


def _arquivamento_motivos_context():
    return [{"key": key, "label": label} for key, label in ARQUIVAMENTO_MOTIVO_CHOICES]


def _filtrar_por_status(queryset, status):
    if status == "arquivados":
        return queryset.filter(etapa="arquivado")
    if status in {"todos", "compartilhados"}:
        return queryset
    return queryset.exclude(etapa="arquivado")


def _resolver_caixa_ids_validos(imoveis):
    caixa_ids_imoveis = {im.caixa_imovel_id for im in imoveis if im.caixa_imovel_id}
    if not caixa_ids_imoveis:
        return set()
    return set(
        ImovelCaixa.objects.filter(imovel_id_caixa__in=caixa_ids_imoveis)
        .values_list("imovel_id_caixa", flat=True)
    )


def _cards_context(imoveis, caixa_ids_validos, user):
    imoveis = list(imoveis)
    imovel_ids = [imovel.pk for imovel in imoveis]
    compartilhamentos = {
        item.imovel_id: item
        for item in ImovelCompartilhamento.objects.filter(
            imovel_id__in=imovel_ids,
            user=user,
            ativo=True,
        )
    }
    cards = []
    for imovel in imoveis:
        compartilhamento = compartilhamentos.get(imovel.pk)
        is_owner = imovel.user_id == user.id
        can_edit = is_owner or (
            compartilhamento is not None and compartilhamento.permissao == PERMISSAO_EDICAO
        )
        cards.append({
            "imovel": imovel,
            "resultado": _resultado_resumo(imovel, imovel.giro_padrao),
            "imagem_url": _imagem_card_url(imovel, caixa_ids_validos),
            "imagem_fallback_url": _imagem_card_fallback_url(imovel, caixa_ids_validos),
            "is_owner": is_owner,
            "is_shared": not is_owner and compartilhamento is not None,
            "can_edit": can_edit,
            "permissao_label": "Proprietário" if is_owner else (compartilhamento.permissao_label if compartilhamento else ""),
            "owner_label": imovel.user.get_full_name() or imovel.user.username,
        })
    return cards


def _aplicar_transicao_etapa(imovel, nova_etapa, motivo_arquivamento=""):
    motivo_valido = motivo_arquivamento if motivo_arquivamento in dict(ARQUIVAMENTO_MOTIVO_CHOICES) else ""
    campos = ["etapa", "updated_at"]

    if nova_etapa == "arquivado":
        imovel.etapa = "arquivado"
        imovel.arquivado_em = timezone.now()
        imovel.motivo_arquivamento = motivo_valido
        campos.extend(["arquivado_em", "motivo_arquivamento"])
    else:
        imovel.etapa = nova_etapa
        if imovel.arquivado_em or imovel.motivo_arquivamento:
            imovel.arquivado_em = None
            imovel.motivo_arquivamento = ""
            campos.extend(["arquivado_em", "motivo_arquivamento"])

    imovel.save(update_fields=list(dict.fromkeys(campos)))


@login_required
def kanban(request):
    imoveis_base = _imoveis_acessiveis_queryset(request.user)
    imoveis_compartilhados_base = _imoveis_compartilhados_queryset(request.user)
    busca = request.GET.get("q", "").strip()
    aba = request.GET.get("aba", "pre")
    abas_validas = {"pre", "pos", "arquivados", "compartilhados", "financeiro"}
    if aba not in abas_validas:
        aba = "pre"

    if busca:
        filtro_busca = (
            Q(endereco__icontains=busca)
            | Q(cidade__icontains=busca)
            | Q(titulo_personalizado__icontains=busca)
        )
        imoveis_base = imoveis_base.filter(filtro_busca)
        imoveis_compartilhados_base = imoveis_compartilhados_base.filter(filtro_busca)

    imoveis_ativos = list(imoveis_base.exclude(etapa="arquivado"))
    imoveis_pre = [im for im in imoveis_ativos if im.etapa in ETAPAS_PRE_KEYS]
    imoveis_pos = [im for im in imoveis_ativos if im.etapa in ETAPAS_POS_KEYS]
    imoveis_arquivados = list(imoveis_base.filter(etapa="arquivado"))
    imoveis_compartilhados = list(imoveis_compartilhados_base)

    caixa_ids_validos = _resolver_caixa_ids_validos(imoveis_ativos + imoveis_arquivados + imoveis_compartilhados)

    def _montar_pipeline(etapas_keys, etapas_labels):
        colunas = []
        for key, label in etapas_labels:
            if key not in etapas_keys:
                continue
            grupo = [im for im in imoveis_ativos if im.etapa == key]
            cards = _cards_context(grupo, caixa_ids_validos, request.user)
            colunas.append({
                "key": key, "label": label, "cor": ETAPA_COR[key], "cards": cards,
                "count": len(cards)
            })
        return colunas

    colunas_pre = _montar_pipeline(ETAPAS_PRE_KEYS, ETAPA_PRE)
    colunas_pos = _montar_pipeline(ETAPAS_POS_KEYS, ETAPA_POS)
    cards_arquivados = _cards_context(imoveis_arquivados, caixa_ids_validos, request.user)
    cards_compartilhados = _cards_context(imoveis_compartilhados, caixa_ids_validos, request.user)

    totais = {}
    for key, _ in ETAPA_CHOICES:
        if key != "arquivado":
            totais[key] = _imoveis_acessiveis_queryset(request.user).filter(etapa=key).count()

    return render(request, "imoveis/kanban.html", {
        "aba": aba,
        "colunas_pre": colunas_pre,
        "colunas_pos": colunas_pos,
        "cards_arquivados": cards_arquivados,
        "cards_compartilhados": cards_compartilhados,
        "totais": totais,
        "busca": busca,
        "total_pre": len(imoveis_pre),
        "total_pos": len(imoveis_pos),
        "total_arquivados": len(imoveis_arquivados),
        "total_compartilhados": len(imoveis_compartilhados),
        "total_geral": len(imoveis_ativos),
        "etapas_menu": _etapas_menu_context(),
        "arquivamento_motivos": _arquivamento_motivos_context(),
        "permissoes_compartilhamento": COMPARTILHAMENTO_PERMISSAO_CHOICES,
    })


@login_required
@require_POST
def atualizar_etapa(request, pk):
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
    nova_etapa = request.POST.get("etapa")
    motivo_arquivamento = request.POST.get("motivo_arquivamento", "").strip()
    etapa_anterior = imovel.etapa
    if nova_etapa in dict(ETAPA_CHOICES):
        if motivo_arquivamento and motivo_arquivamento not in dict(ARQUIVAMENTO_MOTIVO_CHOICES):
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Motivo de arquivamento inválido."}, status=400)
            messages.error(request, "Motivo de arquivamento inválido.")
            return redirect("kanban")

        _aplicar_transicao_etapa(imovel, nova_etapa, motivo_arquivamento=motivo_arquivamento)

        if nova_etapa == "arquivado":
            messages.success(request, f"{imovel.titulo_card} arquivado.")
        elif etapa_anterior == "arquivado":
            messages.success(request, f"{imovel.titulo_card} restaurado para {imovel.etapa_display}.")
        else:
            messages.success(request, f"{imovel.titulo_card} movido para {imovel.etapa_display}.")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "etapa": imovel.etapa,
                "fase": imovel.fase,
                "label": imovel.etapa_display,
                "motivo_arquivamento": imovel.motivo_arquivamento,
                "motivo_arquivamento_label": imovel.motivo_arquivamento_label,
                "arquivado_em": imovel.arquivado_em.isoformat() if imovel.arquivado_em else "",
            })
    elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "error": "Etapa inválida."}, status=400)
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204)
    return redirect("kanban")


@login_required
def listar(request):
    status = request.GET.get("status", "ativos")
    if status not in {"ativos", "arquivados", "compartilhados", "todos"}:
        status = "ativos"

    base_queryset = _imoveis_compartilhados_queryset(request.user) if status == "compartilhados" else _imoveis_acessiveis_queryset(request.user)
    imoveis = list(_filtrar_por_status(base_queryset, status))
    caixa_ids_validos = _resolver_caixa_ids_validos(imoveis)
    cards = _cards_context(imoveis, caixa_ids_validos, request.user)
    totais_status = {
        "ativos": _imoveis_acessiveis_queryset(request.user).exclude(etapa="arquivado").count(),
        "arquivados": _imoveis_acessiveis_queryset(request.user).filter(etapa="arquivado").count(),
        "compartilhados": _imoveis_compartilhados_queryset(request.user).count(),
        "todos": _imoveis_acessiveis_queryset(request.user).count(),
    }
    return render(request, "imoveis/lista.html", {
        "cards": cards,
        "status": status,
        "totais_status": totais_status,
        "etapas_menu": _etapas_menu_context(),
        "arquivamento_motivos": _arquivamento_motivos_context(),
        "permissoes_compartilhamento": COMPARTILHAMENTO_PERMISSAO_CHOICES,
    })


@login_required
def detalhe(request, pk):
    imovel = _get_imovel_com_acesso(pk, request.user)
    acesso = _acesso_context(imovel, request.user)
    if acesso["can_edit"]:
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
    tabelas_cartorio = obter_tabelas_cartorio(imovel.estado, imovel.tipo_leilao)
    if tabelas_cartorio["registro"]:
        if imovel.tipo_leilao == "Extrajudicial" and tabelas_cartorio["escritura"]:
            tab_esc = tabelas_cartorio["escritura"]
            _, _, idx_esc = buscar_faixa(tab_esc, base_cart)
        tab_reg = tabelas_cartorio["registro"]
        _, _, idx_reg = buscar_faixa(tab_reg, base_cart)

    endereco_query = " ".join(
        parte for parte in [imovel.endereco, imovel.cidade, imovel.estado] if parte
    )
    maps_url = f"https://www.google.com/maps/search/?api=1&{urlencode({'query': endereco_query})}"
    maps_embed_url = f"https://maps.google.com/maps?{urlencode({'q': endereco_query, 'output': 'embed'})}"

    imagem_fallback_url = ""
    imagem_url = _foto_upload_url(imovel)
    if not imagem_url and imovel_caixa:
        imagem_url = imovel_caixa.foto_principal_url
        imagem_fallback_url = imovel_caixa.foto_fallback_url

    detalhe_caixa = (imovel_caixa.detalhes or {}).get("detalhe_caixa") if imovel_caixa else {}
    detalhe_caixa = detalhe_caixa or {}

    # Análise jurídica: prefere a análise própria do imóvel (gerada aqui, com todos
    # os documentos); usa a da Caixa como fallback enquanto a local não foi gerada.
    analise_juridica_caixa = (imovel_caixa.detalhes or {}).get("analise_juridica_ia") if imovel_caixa else {}
    analise_juridica_avulso = imovel.analise_juridica_ia or {}
    analise_juridica = analise_juridica_avulso or analise_juridica_caixa
    analise_juridica = analise_juridica or {}
    analise_resultado = analise_juridica.get("resultado") or {}
    analise_nivel_risco = analise_resultado.get("nivel_risco") or "indeterminado"
    # A análise mostrada é a própria do imóvel? (define se podemos pollar o status local)
    analise_origem_avulso = bool(analise_juridica_avulso) or not analise_juridica_caixa

    # A análise pode ser gerada na própria página do imóvel sempre que houver
    # documento analisável (uploads do usuário ou matrícula/edital da Caixa).
    documentos_context = _documentos_context(imovel, imovel_caixa)
    tem_arquivos_analise = documentos_context["tem_arquivos_analise"]
    pode_gerar_analise_avulso = tem_arquivos_analise

    caixa_url = None
    caixa_detalhe_url = None
    if imovel_caixa:
        caixa_url = imovel_caixa.link_caixa or imovel.link_leilao or "https://www.caixa.gov.br/imoveiscaixa"
        caixa_detalhe_url = reverse("leiloes:detalhe", args=[imovel_caixa.imovel_id_caixa])
    elif imovel.link_leilao:
        caixa_url = imovel.link_leilao

    documentos = documentos_context["documentos"]

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

    indicadores_decisao = _indicadores_decisao(
        imovel,
        imovel_caixa,
        r_padrao,
        analise_resultado,
        documentos_context,
    )
    alertas_relatorio = _alertas_relatorio(imovel, imovel_caixa, r_padrao, analise_resultado)
    checklist_operacional = _checklist_context(imovel)
    arquivos = imovel.arquivos.select_related("enviado_por")
    comentarios = imovel.comentarios.select_related("user")
    compartilhamentos = (
        imovel.compartilhamentos
        .filter(ativo=True)
        .select_related("user", "criado_por")
    )

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
        "imagem_fallback_url": imagem_fallback_url,
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
        "analise_origem_avulso": analise_origem_avulso,
        "tem_arquivos_analise": tem_arquivos_analise,
        "indicadores_decisao": indicadores_decisao,
        "alertas_relatorio": alertas_relatorio,
        "checklist_operacional": checklist_operacional,
        "arquivos": arquivos,
        "arquivo_form": ImovelArquivoForm(),
        "calculo_form": ImovelCalculoForm(instance=imovel),
        "comentarios": comentarios,
        "chat_mensagens": chat_historico(imovel),
        "acesso": acesso,
        "compartilhamentos": compartilhamentos,
        "permissoes_compartilhamento": COMPARTILHAMENTO_PERMISSAO_CHOICES,
        "export_rows": export_rows,
    })


@login_required
@require_POST
def atualizar_dados_calculo(request, pk):
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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
    imovel = _get_imovel_com_acesso(pk, request.user, proprietario=True)
    imovel_id = str(imovel.pk)
    nome = imovel.endereco
    imovel.delete()
    messages.success(request, f"🗑️ {nome} excluído.")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "deleted_id": imovel_id})
    return redirect("kanban")


@login_required
@require_POST
def compartilhar_imovel(request, pk):
    imovel = _get_imovel_com_acesso(pk, request.user, proprietario=True)
    destino = request.POST.get("next") or f"{reverse('detalhe', args=[imovel.pk])}#acessos"
    permissao = request.POST.get("permissao", "").strip()
    user_id = request.POST.get("user_id")

    permissoes_validas = dict(COMPARTILHAMENTO_PERMISSAO_CHOICES)
    if permissao not in permissoes_validas:
        messages.error(request, "Selecione uma permissão válida para compartilhar.")
        return redirect(destino)

    try:
        convidado = User.objects.get(pk=user_id, is_active=True)
    except (User.DoesNotExist, TypeError, ValueError):
        messages.error(request, "Usuário selecionado não foi encontrado.")
        return redirect(destino)

    if convidado.pk == request.user.pk:
        messages.error(request, "O proprietário já tem acesso completo ao imóvel.")
        return redirect(destino)

    compartilhamento, criado = ImovelCompartilhamento.objects.get_or_create(
        imovel=imovel,
        user=convidado,
        defaults={
            "permissao": permissao,
            "ativo": True,
            "criado_por": request.user,
        },
    )
    deve_notificar = criado
    if not criado:
        deve_notificar = compartilhamento.permissao != permissao or not compartilhamento.ativo
        compartilhamento.permissao = permissao
        compartilhamento.ativo = True
        compartilhamento.criado_por = request.user
        compartilhamento.save(update_fields=["permissao", "ativo", "criado_por", "atualizado_em"])

    if deve_notificar:
        _criar_notificacao_compartilhamento(compartilhamento, criado=criado)

    nome = _nome_usuario(convidado)
    messages.success(request, f"Acesso de {nome} definido como {permissoes_validas[permissao]}.")
    return redirect(destino)


@login_required
@require_POST
def remover_compartilhamento(request, pk, compartilhamento_id):
    imovel = _get_imovel_com_acesso(pk, request.user, proprietario=True)
    destino = request.POST.get("next") or f"{reverse('detalhe', args=[imovel.pk])}#acessos"
    compartilhamento = get_object_or_404(
        ImovelCompartilhamento,
        pk=compartilhamento_id,
        imovel=imovel,
    )
    nome = _nome_usuario(compartilhamento.user)
    NotificacaoUsuario.objects.filter(
        user=compartilhamento.user,
        imovel=imovel,
        tipo="compartilhamento",
        lida_em__isnull=True,
    ).update(lida_em=timezone.now())
    compartilhamento.delete()
    messages.success(request, f"Acesso de {nome} removido.")
    return redirect(destino)


@login_required
def abrir_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(NotificacaoUsuario, pk=notificacao_id, user=request.user)
    if notificacao.lida_em is None:
        notificacao.lida_em = timezone.now()
        notificacao.save(update_fields=["lida_em"])
    return redirect(notificacao.url or reverse("kanban"))


@login_required
@require_POST
def marcar_notificacoes_lidas(request):
    NotificacaoUsuario.objects.filter(user=request.user, lida_em__isnull=True).update(lida_em=timezone.now())
    destino = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("kanban")
    return redirect(destino)


@login_required
@require_POST
def atualizar_identidade(request, pk):
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
    arquivo = get_object_or_404(ImovelArquivo, pk=arquivo_id, imovel=imovel)
    arquivo.arquivo.delete(save=False)
    arquivo.delete()
    messages.success(request, "Arquivo excluído.")
    return redirect(f"{reverse('detalhe', args=[imovel.pk])}#arquivos")


@login_required
@require_POST
def adicionar_comentario(request, pk):
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)
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


def _imovel_caixa_de(imovel):
    if not imovel.caixa_imovel_id:
        return None
    return ImovelCaixa.objects.filter(imovel_id_caixa=imovel.caixa_imovel_id).first()


def _chat_mensagem_payload(mensagem):
    autor = ""
    if mensagem.role == "user":
        autor = _nome_usuario(mensagem.user) if mensagem.user else "Usuário"
    return {
        "role": mensagem.role,
        "conteudo": mensagem.conteudo,
        "erro": mensagem.erro,
        "autor": autor,
        "criado_em": mensagem.criado_em.isoformat(),
        "criado_em_display": timezone.localtime(mensagem.criado_em).strftime("%d/%m/%Y %H:%M"),
    }


def chat_historico(imovel):
    """Lista de mensagens do chat do imóvel para template/JSON."""
    chat = ChatImovel.objects.filter(imovel=imovel).first()
    if not chat:
        return []
    return [
        _chat_mensagem_payload(msg)
        for msg in chat.mensagens.select_related("user").all()
    ]


@login_required
@require_POST
def enviar_mensagem_chat(request, pk):
    import json as _json
    import logging as _logging
    from .chat import responder_stream, ChatImovelErro
    from .documentos_texto import garantir_textos_documentos

    imovel = _get_imovel_com_acesso(pk, request.user)
    pergunta = (request.POST.get("pergunta") or "").strip()
    if not pergunta:
        return JsonResponse({"ok": False, "erro": "Escreva uma pergunta."}, status=400)

    chat, _ = ChatImovel.objects.get_or_create(imovel=imovel)
    historico = [
        {"role": msg.role, "conteudo": msg.conteudo}
        for msg in chat.mensagens.filter(erro=False)
    ]
    mensagem_usuario = ChatMensagem.objects.create(
        chat=chat, user=request.user, role="user", conteudo=pergunta
    )
    imovel_caixa = _imovel_caixa_de(imovel)

    def _sse(obj):
        return f"data: {_json.dumps(obj, ensure_ascii=False)}\n\n"

    def _erro_assistente(texto):
        msg = ChatMensagem.objects.create(
            chat=chat, role="assistant", conteudo=texto, erro=True
        )
        return _sse({"tipo": "error", "mensagem": _chat_mensagem_payload(msg)})

    def stream():
        # Confirma a mensagem do usuário (versão persistida, com autor/data).
        yield _sse({"tipo": "user", "mensagem": _chat_mensagem_payload(mensagem_usuario)})

        partes = []
        try:
            # Chat roda na web: não dispara navegador (Playwright). Usa o texto já
            # cacheado pela análise; docs da Caixa são baixados ao gerar a análise.
            documentos_cache = garantir_textos_documentos(
                imovel, imovel_caixa, permitir_playwright=False
            )
            for trecho in responder_stream(
                imovel, imovel_caixa, pergunta, historico, documentos_cache
            ):
                if not trecho:
                    continue
                partes.append(trecho)
                yield _sse({"tipo": "delta", "texto": trecho})
        except ChatImovelErro as exc:
            yield _erro_assistente(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            _logging.getLogger(__name__).exception("Erro inesperado no chat do imovel %s", imovel.pk)
            yield _erro_assistente(
                "Não foi possível obter a resposta do assistente. Tente novamente."
            )
            return

        texto = "".join(partes).strip()
        if not texto:
            yield _erro_assistente("O assistente não retornou resposta. Tente novamente.")
            return

        mensagem_resposta = ChatMensagem.objects.create(
            chat=chat, role="assistant", conteudo=texto
        )
        yield _sse({"tipo": "done", "mensagem": _chat_mensagem_payload(mensagem_resposta)})

    resposta = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resposta["Cache-Control"] = "no-cache"
    resposta["X-Accel-Buffering"] = "no"  # evita buffering em proxies (nginx/Railway)
    return resposta


@login_required
def tabela_lances_imovel(request, pk):
    """Retorna tabela de lances progressivos para um imóvel específico."""
    from django.http import JsonResponse
    
    imovel = _get_imovel_com_acesso(pk, request.user)
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
    imovel = _get_imovel_com_acesso(pk, request.user)

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

    modo_compra = request.POST.get("modo_compra", request.GET.get("modo_compra", "financiado"))
    # Se o imóvel só aceita à vista (não pode financiar), assume à vista por padrão.
    if not request.POST.get("modo_compra") and not request.GET.get("modo_compra"):
        if imovel.tipo_pgto == "À Vista":
            modo_compra = "avista"

    params = {
        "modo_compra": modo_compra,
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
    imovel = _get_imovel_com_acesso(pk, request.user, escrita=True)

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
    imovel = _get_imovel_com_acesso(pk, request.user)
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
