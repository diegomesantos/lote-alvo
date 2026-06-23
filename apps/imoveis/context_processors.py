from .models import NotificacaoUsuario


def notificacoes_usuario(request):
    if not request.user.is_authenticated:
        return {
            "notificacoes_nao_lidas_count": 0,
            "notificacoes_recentes": [],
        }

    queryset = NotificacaoUsuario.objects.filter(user=request.user)
    return {
        "notificacoes_nao_lidas_count": queryset.filter(lida_em__isnull=True).count(),
        "notificacoes_recentes": queryset.select_related("imovel", "criado_por")[:8],
    }
