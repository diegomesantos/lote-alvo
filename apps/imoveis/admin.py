from django.contrib import admin
from .models import Imovel


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ("endereco", "cidade", "estado", "etapa", "lance", "caixa_imovel_id", "user", "data_cadastro")
    list_filter = ("etapa", "estado", "tipo_leilao", "tipo_pgto")
    search_fields = ("endereco", "cidade", "caixa_imovel_id", "user__username")
    readonly_fields = ("id", "data_cadastro", "updated_at")
