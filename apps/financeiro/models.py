from django.db import models
from django.contrib.auth.models import User
from apps.imoveis.models import Imovel


class CategoriaFinanceira(models.Model):
    TIPO_CHOICES = [("receita", "Receita"), ("despesa", "Despesa")]
    nome = models.CharField("Nome", max_length=100)
    tipo = models.CharField("Tipo", max_length=10, choices=TIPO_CHOICES)
    icone = models.CharField("Ícone (emoji)", max_length=5, default="💰")

    class Meta:
        ordering = ["tipo", "nome"]
        verbose_name = "Categoria Financeira"
        verbose_name_plural = "Categorias Financeiras"

    def __str__(self):
        return f"{self.icone} {self.nome} ({self.get_tipo_display()})"


class LancamentoFinanceiro(models.Model):
    TIPO_CHOICES = [("receita", "Receita"), ("despesa", "Despesa")]
    STATUS_CHOICES = [
        ("pendente",   "Pendente"),
        ("confirmado", "Confirmado"),
        ("cancelado",  "Cancelado"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lancamentos")
    imovel = models.ForeignKey(Imovel, on_delete=models.CASCADE, related_name="lancamentos",
                                null=True, blank=True)
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="lancamentos")
    tipo = models.CharField("Tipo", max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField("Descrição", max_length=200)
    valor = models.DecimalField("Valor (R$)", max_digits=14, decimal_places=2)
    data = models.DateField("Data")
    status = models.CharField("Status", max_length=15, choices=STATUS_CHOICES, default="confirmado")
    obs = models.TextField("Observações", blank=True)
    comprovante = models.FileField("Comprovante", upload_to="comprovantes/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-created_at"]
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"

    def __str__(self):
        return f"{self.descricao} — {self.valor} ({self.data})"

    @property
    def sinal(self):
        return 1 if self.tipo == "receita" else -1
