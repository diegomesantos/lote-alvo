from django.conf import settings
from django.db import models
from django.utils import timezone


class CartorioTabela(models.Model):
    TIPO_ESCRITURA = "escritura"
    TIPO_REGISTRO = "registro"
    TIPO_CHOICES = [
        (TIPO_ESCRITURA, "Escritura"),
        (TIPO_REGISTRO, "Registro"),
    ]

    STATUS_PENDENTE = "pendente_validacao"
    STATUS_VALIDADA = "validada"
    STATUS_SUBSTITUIDA = "substituida"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente de validação"),
        (STATUS_VALIDADA, "Validada"),
        (STATUS_SUBSTITUIDA, "Substituída"),
    ]

    uf = models.CharField("UF", max_length=2, db_index=True)
    ano = models.PositiveSmallIntegerField("Ano", db_index=True)
    tipo = models.CharField("Tipo", max_length=20, choices=TIPO_CHOICES, db_index=True)
    vigente_inicio = models.DateField("Início da vigência", db_index=True)
    vigente_fim = models.DateField("Fim da vigência", null=True, blank=True, db_index=True)
    fonte_nome = models.CharField("Fonte", max_length=180)
    fonte_url = models.URLField("URL da fonte oficial", max_length=600, blank=True)
    fundamento = models.CharField("Fundamento/ato normativo", max_length=220, blank=True)
    observacoes = models.TextField("Observações", blank=True)
    status = models.CharField(
        "Status",
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
        db_index=True,
    )
    ativo = models.BooleanField("Ativa", default=True, db_index=True)
    conferido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Conferido por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cartorio_tabelas_conferidas",
    )
    conferido_em = models.DateTimeField("Conferido em", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["uf", "-vigente_inicio", "tipo"]
        indexes = [
            models.Index(fields=["uf", "tipo", "ativo", "vigente_inicio"]),
            models.Index(fields=["uf", "ano", "tipo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["uf", "ano", "tipo", "vigente_inicio"],
                name="uniq_cartorio_tabela_uf_ano_tipo_vigencia",
            ),
        ]
        verbose_name = "Tabela cartorária"
        verbose_name_plural = "Tabelas cartorárias"

    def __str__(self):
        return f"{self.uf} {self.ano} - {self.get_tipo_display()}"

    @property
    def vigente_label(self):
        inicio = self.vigente_inicio.strftime("%d/%m/%Y")
        if self.vigente_fim:
            return f"{inicio} a {self.vigente_fim.strftime('%d/%m/%Y')}"
        return f"desde {inicio}"

    def marcar_validada(self, user=None):
        self.status = self.STATUS_VALIDADA
        self.conferido_por = user
        self.conferido_em = timezone.now()


class CartorioFaixa(models.Model):
    tabela = models.ForeignKey(CartorioTabela, on_delete=models.CASCADE, related_name="faixas")
    ordem = models.PositiveSmallIntegerField("Ordem")
    limite_superior = models.DecimalField(
        "Limite superior",
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Deixe vazio para representar a última faixa sem limite.",
    )
    valor = models.DecimalField("Valor do emolumento", max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["tabela", "ordem"]
        indexes = [
            models.Index(fields=["tabela", "ordem"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tabela", "ordem"], name="uniq_cartorio_faixa_ordem"),
        ]
        verbose_name = "Faixa cartorária"
        verbose_name_plural = "Faixas cartorárias"

    def __str__(self):
        limite = "sem limite" if self.limite_superior is None else f"até R$ {self.limite_superior}"
        return f"{self.tabela} - {limite}: R$ {self.valor}"


class CartorioRegraExtra(models.Model):
    STATUS_PENDENTE = CartorioTabela.STATUS_PENDENTE
    STATUS_VALIDADA = CartorioTabela.STATUS_VALIDADA
    STATUS_SUBSTITUIDA = CartorioTabela.STATUS_SUBSTITUIDA
    STATUS_CHOICES = CartorioTabela.STATUS_CHOICES

    uf = models.CharField("UF", max_length=2, db_index=True)
    ano = models.PositiveSmallIntegerField("Ano", db_index=True)
    nome = models.CharField("Nome", max_length=80)
    percentual = models.DecimalField(
        "Percentual (%)",
        max_digits=7,
        decimal_places=4,
        help_text="Ex.: 0,1000 para 0,1%.",
    )
    vigente_inicio = models.DateField("Início da vigência", db_index=True)
    vigente_fim = models.DateField("Fim da vigência", null=True, blank=True, db_index=True)
    fonte_nome = models.CharField("Fonte", max_length=180)
    fonte_url = models.URLField("URL da fonte oficial", max_length=600, blank=True)
    fundamento = models.CharField("Fundamento/ato normativo", max_length=220, blank=True)
    observacoes = models.TextField("Observações", blank=True)
    status = models.CharField(
        "Status",
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
        db_index=True,
    )
    ativo = models.BooleanField("Ativa", default=True, db_index=True)
    conferido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Conferido por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cartorio_extras_conferidos",
    )
    conferido_em = models.DateTimeField("Conferido em", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["uf", "-vigente_inicio", "nome"]
        indexes = [
            models.Index(fields=["uf", "ativo", "vigente_inicio"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["uf", "ano", "nome", "vigente_inicio"],
                name="uniq_cartorio_extra_uf_ano_nome_vigencia",
            ),
        ]
        verbose_name = "Regra extra cartorária"
        verbose_name_plural = "Regras extras cartorárias"

    def __str__(self):
        return f"{self.uf} {self.ano} - {self.nome} ({self.percentual}%)"

    @property
    def vigente_label(self):
        inicio = self.vigente_inicio.strftime("%d/%m/%Y")
        if self.vigente_fim:
            return f"{inicio} a {self.vigente_fim.strftime('%d/%m/%Y')}"
        return f"desde {inicio}"


class CartorioFonteMonitorada(models.Model):
    uf = models.CharField("UF", max_length=2, db_index=True)
    nome = models.CharField("Nome", max_length=180)
    url = models.URLField("URL oficial monitorada", max_length=600, unique=True)
    ativa = models.BooleanField("Ativa", default=True, db_index=True)
    observacoes = models.TextField("Observações", blank=True)
    ultimo_hash = models.CharField("Último hash", max_length=64, blank=True)
    ultimo_status_http = models.PositiveSmallIntegerField("Último status HTTP", null=True, blank=True)
    ultimo_content_type = models.CharField("Último content-type", max_length=180, blank=True)
    ultimo_tamanho_bytes = models.PositiveIntegerField("Último tamanho em bytes", null=True, blank=True)
    ultimo_etag = models.CharField("Último ETag", max_length=255, blank=True)
    ultimo_last_modified = models.CharField("Último Last-Modified", max_length=255, blank=True)
    verificada_em = models.DateTimeField("Verificada em", null=True, blank=True)
    alterada_em = models.DateTimeField("Alterada em", null=True, blank=True)
    ultimo_erro = models.TextField("Último erro", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["uf", "nome"]
        indexes = [
            models.Index(fields=["uf", "ativa"]),
            models.Index(fields=["ativa", "verificada_em"]),
        ]
        verbose_name = "Fonte cartorária monitorada"
        verbose_name_plural = "Fontes cartorárias monitoradas"

    def __str__(self):
        return f"{self.uf} - {self.nome}"


class CartorioFonteEvento(models.Model):
    TIPO_MUDANCA = "mudanca_detectada"
    TIPO_ERRO = "erro"
    TIPO_CHOICES = [
        (TIPO_MUDANCA, "Mudança detectada"),
        (TIPO_ERRO, "Erro de monitoramento"),
    ]

    STATUS_PENDENTE = "pendente"
    STATUS_REVISADO = "revisado"
    STATUS_IGNORADO = "ignorado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_REVISADO, "Revisado"),
        (STATUS_IGNORADO, "Ignorado"),
    ]

    fonte = models.ForeignKey(
        CartorioFonteMonitorada,
        on_delete=models.CASCADE,
        related_name="eventos",
        verbose_name="Fonte",
    )
    tipo = models.CharField("Tipo", max_length=30, choices=TIPO_CHOICES, db_index=True)
    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
        db_index=True,
    )
    hash_anterior = models.CharField("Hash anterior", max_length=64, blank=True)
    hash_novo = models.CharField("Hash novo", max_length=64, blank=True)
    status_http = models.PositiveSmallIntegerField("Status HTTP", null=True, blank=True)
    content_type = models.CharField("Content-type", max_length=180, blank=True)
    tamanho_bytes = models.PositiveIntegerField("Tamanho em bytes", null=True, blank=True)
    mensagem = models.CharField("Mensagem", max_length=260)
    detalhe = models.TextField("Detalhe", blank=True)
    aplicacao_automatica = models.BooleanField("Aplicação automática", default=False)
    tabelas_afetadas = models.PositiveSmallIntegerField("Tabelas afetadas", default=0)
    extras_afetados = models.PositiveSmallIntegerField("Regras extras afetadas", default=0)
    detectado_em = models.DateTimeField("Detectado em", auto_now_add=True)
    resolvido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Resolvido por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cartorio_fonte_eventos_resolvidos",
    )
    resolvido_em = models.DateTimeField("Resolvido em", null=True, blank=True)

    class Meta:
        ordering = ["-detectado_em"]
        indexes = [
            models.Index(fields=["status", "tipo", "detectado_em"]),
            models.Index(fields=["fonte", "status"]),
        ]
        verbose_name = "Evento de fonte cartorária"
        verbose_name_plural = "Eventos de fonte cartorária"

    def __str__(self):
        return f"{self.fonte} - {self.get_tipo_display()} ({self.get_status_display()})"

    def marcar_revisado(self, user=None):
        self.status = self.STATUS_REVISADO
        self.resolvido_por = user
        self.resolvido_em = timezone.now()

    def marcar_ignorado(self, user=None):
        self.status = self.STATUS_IGNORADO
        self.resolvido_por = user
        self.resolvido_em = timezone.now()
