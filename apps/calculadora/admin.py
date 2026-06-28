from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CartorioFaixa,
    CartorioFonteEvento,
    CartorioFonteMonitorada,
    CartorioRegraExtra,
    CartorioTabela,
)


class CartorioFaixaInline(admin.TabularInline):
    model = CartorioFaixa
    extra = 1
    fields = ("ordem", "limite_superior", "valor")
    ordering = ("ordem",)


@admin.register(CartorioTabela)
class CartorioTabelaAdmin(admin.ModelAdmin):
    list_display = (
        "uf",
        "ano",
        "tipo",
        "status",
        "ativo",
        "vigente_inicio",
        "vigente_fim",
        "fonte_nome",
        "atualizado_em",
    )
    list_filter = ("uf", "ano", "tipo", "status", "ativo")
    search_fields = ("uf", "fonte_nome", "fonte_url", "fundamento", "observacoes")
    readonly_fields = ("criado_em", "atualizado_em", "conferido_em")
    inlines = [CartorioFaixaInline]
    actions = ["marcar_como_validada", "desativar_tabelas"]

    @admin.action(description="Marcar selecionadas como validadas")
    def marcar_como_validada(self, request, queryset):
        for tabela in queryset:
            tabela.marcar_validada(request.user)
            tabela.save(update_fields=["status", "conferido_por", "conferido_em", "atualizado_em"])

    @admin.action(description="Desativar selecionadas")
    def desativar_tabelas(self, request, queryset):
        queryset.update(ativo=False)


@admin.register(CartorioRegraExtra)
class CartorioRegraExtraAdmin(admin.ModelAdmin):
    list_display = (
        "uf",
        "ano",
        "nome",
        "percentual",
        "status",
        "ativo",
        "vigente_inicio",
        "vigente_fim",
        "fonte_nome",
        "atualizado_em",
    )
    list_filter = ("uf", "ano", "status", "ativo")
    search_fields = ("uf", "nome", "fonte_nome", "fonte_url", "fundamento", "observacoes")
    readonly_fields = ("criado_em", "atualizado_em", "conferido_em")


@admin.register(CartorioFonteMonitorada)
class CartorioFonteMonitoradaAdmin(admin.ModelAdmin):
    list_display = (
        "uf",
        "nome",
        "ativa",
        "link_fonte",
        "verificada_em",
        "alterada_em",
        "ultimo_status_http",
        "ultimo_tamanho_bytes",
    )
    list_filter = ("uf", "ativa", "ultimo_status_http")
    search_fields = ("uf", "nome", "url", "observacoes", "ultimo_erro")
    readonly_fields = (
        "ultimo_hash",
        "ultimo_status_http",
        "ultimo_content_type",
        "ultimo_tamanho_bytes",
        "ultimo_etag",
        "ultimo_last_modified",
        "verificada_em",
        "alterada_em",
        "ultimo_erro",
        "criado_em",
        "atualizado_em",
    )

    @admin.display(description="Fonte oficial")
    def link_fonte(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">abrir fonte</a>', obj.url)


@admin.register(CartorioFonteEvento)
class CartorioFonteEventoAdmin(admin.ModelAdmin):
    list_display = (
        "fonte",
        "tipo",
        "status",
        "mensagem",
        "aplicacao_automatica",
        "tabelas_afetadas",
        "extras_afetados",
        "detectado_em",
        "resolvido_por",
        "resolvido_em",
    )
    list_filter = ("status", "tipo", "fonte__uf")
    search_fields = ("fonte__uf", "fonte__nome", "fonte__url", "mensagem", "detalhe")
    readonly_fields = (
        "fonte",
        "tipo",
        "hash_anterior",
        "hash_novo",
        "status_http",
        "content_type",
        "tamanho_bytes",
        "mensagem",
        "detalhe",
        "aplicacao_automatica",
        "tabelas_afetadas",
        "extras_afetados",
        "detectado_em",
        "resolvido_por",
        "resolvido_em",
    )
    actions = ["marcar_como_revisado", "marcar_como_ignorado"]

    @admin.action(description="Marcar eventos selecionados como revisados")
    def marcar_como_revisado(self, request, queryset):
        for evento in queryset:
            evento.marcar_revisado(request.user)
            evento.save(update_fields=["status", "resolvido_por", "resolvido_em"])

    @admin.action(description="Marcar eventos selecionados como ignorados")
    def marcar_como_ignorado(self, request, queryset):
        for evento in queryset:
            evento.marcar_ignorado(request.user)
            evento.save(update_fields=["status", "resolvido_por", "resolvido_em"])
