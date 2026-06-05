from django.contrib import admin
from .models import Imovel, ImovelArquivo, ImovelChecklistItem, ImovelComentario


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ("titulo_card", "cidade", "estado", "etapa", "lance", "caixa_imovel_id", "user", "data_cadastro")
    list_filter = ("etapa", "estado", "tipo_leilao", "tipo_pgto")
    search_fields = ("titulo_personalizado", "endereco", "cidade", "caixa_imovel_id", "user__username", "user__email")
    readonly_fields = ("id", "data_cadastro", "updated_at")


@admin.register(ImovelChecklistItem)
class ImovelChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("texto", "imovel", "etapa", "concluido", "ordem", "atualizado_em")
    list_filter = ("etapa", "concluido")
    search_fields = ("texto", "imovel__endereco", "imovel__titulo_personalizado")


@admin.register(ImovelArquivo)
class ImovelArquivoAdmin(admin.ModelAdmin):
    list_display = ("nome_exibicao", "imovel", "categoria", "enviado_por", "criado_em")
    list_filter = ("categoria", "criado_em")
    search_fields = ("nome", "arquivo", "imovel__endereco", "imovel__titulo_personalizado")


@admin.register(ImovelComentario)
class ImovelComentarioAdmin(admin.ModelAdmin):
    list_display = ("imovel", "user", "criado_em")
    search_fields = ("texto", "imovel__endereco", "imovel__titulo_personalizado", "user__username", "user__email")
