from django.contrib import admin
from .models import ImovelCaixa


@admin.register(ImovelCaixa)
class ImovelCaixaAdmin(admin.ModelAdmin):
    list_display = (
        'imovel_id_caixa',
        'endereco',
        'cidade',
        'estado',
        'tipo',
        'modalidade_venda',
        'valor_avaliacao',
        'percentual_desconto',
        'data_leilao',
        'ativo_caixa',
        'detalhe_atualizado_em',
    )
    list_filter = ('ativo_caixa', 'estado', 'cidade', 'tipo', 'modalidade_venda', 'data_leilao', 'ocupado')
    search_fields = ('imovel_id_caixa', 'endereco', 'cidade', 'bairro')
    readonly_fields = (
        'sincronizado_em',
        'atualizado_em',
        'ultima_sincronizacao_caixa',
        'removido_da_caixa_em',
        'detalhe_atualizado_em',
    )

    fieldsets = (
        ('Identificação', {
            'fields': ('imovel_id_caixa', 'endereco', 'bairro', 'cidade', 'estado', 'cep', 'link_caixa')
        }),
        ('Características', {
            'fields': ('tipo', 'quartos', 'area_total', 'area_util', 'area_terreno', 'descricao')
        }),
        ('Valores', {
            'fields': ('valor_avaliacao', 'percentual_desconto', 'valor_minimo_lance', 'valor_final')
        }),
        ('Leilão', {
            'fields': ('modalidade_venda', 'data_leilao', 'hora_leilao', 'tipo_leilao')
        }),
        ('Formas de Pagamento', {
            'fields': ('formas_pagamento',)
        }),
        ('Documentação', {
            'fields': ('edital_url', 'matricula_url', 'foto_url')
        }),
        ('Status', {
            'fields': ('ativo_caixa', 'situacao', 'ocupado', 'pendencias', 'possui_penhora')
        }),
        ('Detalhes Caixa', {
            'fields': ('detalhes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'data_geracao_lista',
                'ultima_sincronizacao_caixa',
                'removido_da_caixa_em',
                'detalhe_atualizado_em',
                'sincronizado_em',
                'atualizado_em',
            ),
            'classes': ('collapse',)
        }),
    )
