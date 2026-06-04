import uuid
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from core.calculos.cartorio import TODOS_ESTADOS, ESTADOS_NOMES


# ── Pipeline Pré-Arrematação ────────────────────────────────────────────────
ETAPA_PRE = [
    ("estoque",            "Estoque"),
    ("triagem_financeira", "Triagem Financeira"),
    ("triagem_juridica",   "Triagem Jurídica"),
    ("debate_final",       "Debate Final e Decisão"),
    ("participacao_leilao","Participação Leilão"),
]

# ── Pipeline Pós-Arrematação ────────────────────────────────────────────────
ETAPA_POS = [
    ("registro_desocupacao", "Registro e Desocupação"),
    ("reforma",              "Reforma"),
    ("procedimento_venda",   "Procedimento de Venda"),
    ("vendido_ir",           "Vendido (Aguardando IR)"),
    ("operacao_finalizada",  "Operação Finalizada"),
]

ETAPA_CHOICES = ETAPA_PRE + ETAPA_POS + [("arquivado", "Arquivado")]

ETAPA_COR = {
    # Pré
    "estoque":             "#6366f1",
    "triagem_financeira":  "#f59e0b",
    "triagem_juridica":    "#8b5cf6",
    "debate_final":        "#ec4899",
    "participacao_leilao": "#f97316",
    # Pós
    "registro_desocupacao":"#f97316",
    "reforma":             "#8b5cf6",
    "procedimento_venda":  "#3b82f6",
    "vendido_ir":          "#10b981",
    "operacao_finalizada": "#22c55e",
    # Arquivado
    "arquivado":           "#6b7280",
}

ETAPAS_PRE_KEYS  = [k for k, _ in ETAPA_PRE]
ETAPAS_POS_KEYS  = [k for k, _ in ETAPA_POS]

TIPO_LEILAO_CHOICES = [
    ("Extrajudicial", "Extrajudicial"),
    ("Judicial",      "Judicial"),
]

TIPO_PGTO_CHOICES = [
    ("À Vista",           "À Vista"),
    ("Financiamento SAC", "Financiamento SAC"),
]

ITBI_BASE_CHOICES = [
    ("Arrematação",     "Arrematação"),
    ("Avaliação Fiscal", "Avaliação Fiscal"),
]

MODO_CARTORIO_CHOICES = [
    ("Automático", "Automático"),
    ("Manual",     "Manual"),
]

TIPO_PESSOA_CHOICES = [
    ("Pessoa Física",   "Pessoa Física"),
    ("Pessoa Jurídica", "Pessoa Jurídica"),
]

TIPO_IMOVEL_CHOICES = [
    ("apartamento", "Apartamento"),
    ("casa",        "Casa"),
    ("terreno",     "Terreno"),
    ("comercial",   "Comercial"),
    ("rural",       "Rural"),
    ("outros",      "Outros"),
]

PRIORIDADE_CHOICES = [
    ("baixa",   "Baixa"),
    ("media",   "Média"),
    ("alta",    "Alta"),
    ("urgente", "Urgente"),
]

PRIORIDADE_COR = {
    "baixa":   ("#dcfce7", "#166534"),
    "media":   ("#fef9c3", "#854d0e"),
    "alta":    ("#ffedd5", "#c2410c"),
    "urgente": ("#fee2e2", "#991b1b"),
}

GIRO_MESES_CHOICES = [(m, f"{m} meses") for m in [1, 3, 4, 6, 7, 9, 10, 12]]
ESTADO_CHOICES = [(uf, f"{uf} — {ESTADOS_NOMES.get(uf, uf)}") for uf in TODOS_ESTADOS]


class Imovel(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="imoveis")

    # Identificação
    endereco     = models.CharField("Endereço", max_length=200)
    cidade       = models.CharField("Cidade", max_length=100)
    estado       = models.CharField("Estado (UF)", max_length=2, choices=ESTADO_CHOICES, default="BA")
    tipo_imovel  = models.CharField("Tipo de imóvel", max_length=20, choices=TIPO_IMOVEL_CHOICES, default="apartamento")
    etapa        = models.CharField("Etapa", max_length=30, choices=ETAPA_CHOICES, default="estoque")
    prioridade   = models.CharField("Prioridade", max_length=10, choices=PRIORIDADE_CHOICES, default="media")
    tipo_leilao  = models.CharField("Tipo de leilão", max_length=20, choices=TIPO_LEILAO_CHOICES, default="Extrajudicial")
    data_leilao  = models.DateField("Data do leilão", null=True, blank=True)
    link_leilao  = models.URLField("Link do leilão", blank=True)
    foto         = models.ImageField("Foto", upload_to="imoveis/fotos/", null=True, blank=True)
    obs          = models.TextField("Observações", blank=True)
    caixa_imovel_id = models.CharField("ID do imóvel Caixa", max_length=50, blank=True, db_index=True)

    # Valores
    avaliacao = models.DecimalField("Valor de avaliação (R$)", max_digits=14, decimal_places=2, default=0)
    lance     = models.DecimalField("Lance (R$)", max_digits=14, decimal_places=2, default=0)

    # Pagamento
    tipo_pgto  = models.CharField("Pagamento", max_length=20, choices=TIPO_PGTO_CHOICES, default="À Vista")
    entrada    = models.DecimalField("Entrada (%)", max_digits=5, decimal_places=2, default=100)
    prazo_fin  = models.PositiveIntegerField("Prazo financiamento (meses)", default=0)
    cet_aa     = models.DecimalField("CET (% a.a.)", max_digits=5, decimal_places=2, default=0)

    # Receitas
    preco_venda    = models.DecimalField("Preço de venda (R$)", max_digits=14, decimal_places=2, default=0)
    taxa_acrescimo = models.DecimalField("Taxa acréscimo venda (%)", max_digits=5, decimal_places=2, default=0)
    desconto_venda = models.DecimalField("Desconto venda (%)", max_digits=5, decimal_places=2, default=0)
    rec_aluguel_am = models.DecimalField("Receita aluguel/mês (R$)", max_digits=12, decimal_places=2, default=0)
    pct_corretor   = models.DecimalField("Corretor (%)", max_digits=5, decimal_places=2, default=5)

    # ITBI
    pct_itbi_base = models.CharField("Base ITBI", max_length=20, choices=ITBI_BASE_CHOICES, default="Arrematação")
    aliq_itbi     = models.DecimalField("Alíquota ITBI (%)", max_digits=5, decimal_places=2, default=2)
    aliq_itbi_fin = models.DecimalField("Alíq. fração financiada (%)", max_digits=5, decimal_places=2, default=0)

    # Cartório
    modo_cartorio    = models.CharField("Modo cartório", max_length=10, choices=MODO_CARTORIO_CHOICES, default="Automático")
    av_fiscal        = models.DecimalField("Avaliação fiscal (R$)", max_digits=14, decimal_places=2, default=0)
    escritura_manual = models.DecimalField("Escritura manual (R$)", max_digits=12, decimal_places=2, default=0)
    registro_manual  = models.DecimalField("Registro manual (R$)", max_digits=12, decimal_places=2, default=0)

    # Despesas
    pct_leiloeiro = models.DecimalField("Comissão leiloeiro (%)", max_digits=5, decimal_places=2, default=5)
    reformas      = models.DecimalField("Reformas (R$)", max_digits=12, decimal_places=2, default=0)
    custo_desocup = models.DecimalField("Custo desocupação (R$)", max_digits=12, decimal_places=2, default=0)
    debitos       = models.DecimalField("Débitos (R$)", max_digits=12, decimal_places=2, default=0)
    despesas_div  = models.DecimalField("Despesas diversas (R$)", max_digits=12, decimal_places=2, default=0)
    laudemio_pct  = models.DecimalField("Laudêmio (%)", max_digits=5, decimal_places=2, default=0)
    meses_titulo  = models.PositiveIntegerField("Meses até título", default=0)

    # Recorrentes
    iptu_am = models.DecimalField("IPTU mensal (R$)", max_digits=10, decimal_places=2, default=0)
    cond_am = models.DecimalField("Condomínio mensal (R$)", max_digits=10, decimal_places=2, default=0)

    # Custo oportunidade & IR
    custo_oport_aa = models.DecimalField("Rendimento alternativo (% a.a.)", max_digits=5, decimal_places=2, default=0)
    tipo_pessoa    = models.CharField("Tributação IR", max_length=20, choices=TIPO_PESSOA_CHOICES, default="Pessoa Física")

    # Simulação
    lucro_minimo    = models.DecimalField("Lucro mínimo desejado (R$)", max_digits=12, decimal_places=2, default=0)
    incremento_lance= models.DecimalField("Incremento de lance (R$)", max_digits=12, decimal_places=2, default=5000)
    giro_padrao     = models.IntegerField("Giro padrão (meses)", choices=GIRO_MESES_CHOICES, default=12)

    # Metadata
    data_cadastro = models.DateField("Data de cadastro", auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_cadastro"]
        verbose_name = "Imóvel"
        verbose_name_plural = "Imóveis"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "caixa_imovel_id"],
                condition=~Q(caixa_imovel_id=""),
                name="unique_imovel_caixa_por_usuario",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_imovel_display()} — {self.endereco}, {self.cidade}/{self.estado}"

    @property
    def titulo_card(self):
        tipo = self.get_tipo_imovel_display().upper()
        return f"{tipo} em {self.cidade.upper()}, {self.estado}"

    @property
    def etapa_display(self):
        return dict(ETAPA_CHOICES).get(self.etapa, self.etapa)

    @property
    def etapa_cor(self):
        return ETAPA_COR.get(self.etapa, "#888")

    @property
    def prioridade_cores(self):
        return PRIORIDADE_COR.get(self.prioridade, ("#f3f4f6", "#6b7280"))

    @property
    def fase(self):
        if self.etapa in ETAPAS_PRE_KEYS:
            return "pre"
        elif self.etapa in ETAPAS_POS_KEYS:
            return "pos"
        return "arquivado"

    @property
    def desconto_pct(self):
        if self.avaliacao and self.avaliacao > 0:
            return (1 - float(self.lance) / float(self.avaliacao)) * 100
        return 0

    def to_calc_dict(self):
        return {
            "lance":           float(self.lance),
            "avaliacao":       float(self.avaliacao),
            "preco_venda":     float(self.preco_venda),
            "taxa_acrescimo":  float(self.taxa_acrescimo),
            "desconto_venda":  float(self.desconto_venda),
            "tipo_pgto":       self.tipo_pgto,
            "entrada":         float(self.entrada),
            "prazo_fin":       int(self.prazo_fin),
            "cet_aa":          float(self.cet_aa),
            "pct_leiloeiro":   float(self.pct_leiloeiro),
            "aliq_itbi":       float(self.aliq_itbi),
            "aliq_itbi_fin":   float(self.aliq_itbi_fin),
            "pct_itbi_base":   self.pct_itbi_base,
            "av_fiscal":       float(self.av_fiscal),
            "estado":          self.estado,
            "tipo_leilao":     self.tipo_leilao,
            "modo_cartorio":   self.modo_cartorio,
            "escritura_manual":float(self.escritura_manual),
            "registro_manual": float(self.registro_manual),
            "reformas":        float(self.reformas),
            "custo_desocup":   float(self.custo_desocup),
            "debitos":         float(self.debitos),
            "despesas_div":    float(self.despesas_div),
            "laudemio_pct":    float(self.laudemio_pct),
            "meses_titulo":    int(self.meses_titulo),
            "iptu_am":         float(self.iptu_am),
            "cond_am":         float(self.cond_am),
            "custo_oport_aa":  float(self.custo_oport_aa),
            "tipo_pessoa":     self.tipo_pessoa,
            "pct_corretor":    float(self.pct_corretor),
            "rec_aluguel_am":  float(self.rec_aluguel_am),
            "lucro_minimo":    float(self.lucro_minimo),
            "incremento_lance":float(self.incremento_lance),
        }
