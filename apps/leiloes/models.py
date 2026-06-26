from django.db import models


CAIXA_FOTOS_BASE_URL = "https://venda-imoveis.caixa.gov.br/fotos"


class ImovelCaixa(models.Model):
    TIPO_CHOICES = [
        ('apto', 'Apartamento'),
        ('casa', 'Casa'),
        ('sala', 'Sala Comercial'),
        ('lote', 'Lote'),
        ('galpao', 'Galpão'),
        ('outro', 'Outro'),
    ]

    TIPO_LEILAO_CHOICES = [
        ('extra', 'Extrajudicial'),
        ('judicial', 'Judicial'),
    ]

    # Responsabilidade por despesas (condomínio / tributos) conforme regras da Caixa
    DESPESA_CHOICES = [
        ('comprador', 'Por conta do comprador'),
        ('comprador_ate_10', 'Comprador até 10% (Caixa paga o excedente)'),
        ('caixa', 'Quitado pela Caixa'),
        ('indeterminado', 'Não informado'),
    ]

    # Identificação
    imovel_id_caixa = models.CharField(unique=True, max_length=50)
    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100, db_index=True)
    estado = models.CharField(max_length=2, db_index=True)
    bairro = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    cep = models.CharField(max_length=10, null=True, blank=True)

    # Características
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    quartos = models.IntegerField(null=True, blank=True)
    area_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    area_util = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    area_terreno = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    descricao = models.TextField(blank=True)

    # Valores
    valor_avaliacao = models.DecimalField(max_digits=12, decimal_places=2)
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2)
    valor_minimo_lance = models.DecimalField(max_digits=12, decimal_places=2)
    valor_final = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Leilão
    data_leilao = models.DateField(null=True, blank=True, db_index=True)
    hora_leilao = models.TimeField(null=True, blank=True)
    tipo_leilao = models.CharField(max_length=20, choices=TIPO_LEILAO_CHOICES)
    modalidade_venda = models.CharField(max_length=100, blank=True, db_index=True)

    # Regras de pagamento das despesas (extraídas de regras_pagamento_texto no enriquecimento)
    despesa_condominio = models.CharField(
        max_length=20, choices=DESPESA_CHOICES, default='indeterminado', db_index=True
    )
    despesa_tributos = models.CharField(
        max_length=20, choices=DESPESA_CHOICES, default='indeterminado', db_index=True
    )

    # Formas de Pagamento (usando JSONField)
    formas_pagamento = models.JSONField(default=dict)

    # URLs
    edital_url = models.URLField(null=True, blank=True)
    matricula_url = models.URLField(null=True, blank=True)
    foto_url = models.URLField(null=True, blank=True)
    link_caixa = models.URLField(max_length=500, null=True, blank=True)

    # Status
    ativo_caixa = models.BooleanField(default=True, db_index=True)
    ocupado = models.BooleanField(default=False)
    situacao = models.CharField(max_length=100, blank=True)
    pendencias = models.JSONField(default=list)
    possui_penhora = models.BooleanField(default=False)
    detalhes = models.JSONField(default=dict, blank=True)

    # Metadata
    data_geracao_lista = models.DateField(null=True, blank=True)
    ultima_sincronizacao_caixa = models.DateTimeField(null=True, blank=True, db_index=True)
    removido_da_caixa_em = models.DateTimeField(null=True, blank=True)
    detalhe_atualizado_em = models.DateTimeField(null=True, blank=True)
    sincronizado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_leilao', '-valor_avaliacao']
        verbose_name = 'Imóvel Caixa'
        verbose_name_plural = 'Imóveis Caixa'

    def __str__(self):
        return f"{self.endereco} - {self.cidade}/{self.estado}"

    def _foto_caixa_url(self, sufixo):
        return f"{CAIXA_FOTOS_BASE_URL}/F{self.imovel_id_caixa}{sufixo}.jpg"

    @property
    def foto_principal_url(self):
        if self.foto_url and self.foto_url.startswith(f"{CAIXA_FOTOS_BASE_URL}/"):
            return self.foto_url
        return self._foto_caixa_url("21")

    @property
    def foto_fallback_url(self):
        principal = self.foto_principal_url
        for sufixo in ("21", "22"):
            candidato = self._foto_caixa_url(sufixo)
            if candidato != principal:
                return candidato
        return ""

    @property
    def valor_desconto_reais(self):
        return self.valor_avaliacao - self.valor_minimo_lance

    @property
    def pode_financiar(self):
        return self.formas_pagamento.get('financiamento', False)

    @property
    def pode_fgts(self):
        return self.formas_pagamento.get('fgts', False)

    @property
    def pode_consorcio(self):
        return self.formas_pagamento.get('consorcio', False)

    @property
    def valor_por_m2(self):
        if self.area_util and self.area_util > 0:
            return float(self.valor_minimo_lance) / float(self.area_util)
        return None
