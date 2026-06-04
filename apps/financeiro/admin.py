from django.contrib import admin
from .models import CategoriaFinanceira, LancamentoFinanceiro


@admin.register(CategoriaFinanceira)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("icone", "nome", "tipo")
    list_filter = ("tipo",)


@admin.register(LancamentoFinanceiro)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "tipo", "valor", "data", "status", "imovel", "user")
    list_filter = ("tipo", "status")
    search_fields = ("descricao", "user__username")
