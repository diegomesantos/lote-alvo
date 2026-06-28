from django.contrib import admin

from .models import CartorioFaixa, CartorioRegraExtra, CartorioTabela


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
