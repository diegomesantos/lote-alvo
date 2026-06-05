from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.imoveis.models import Imovel
from .models import CategoriaFinanceira, LancamentoFinanceiro


class FinanceiroInteracaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="financeiro",
            email="financeiro@example.com",
            password="senha123",
        )
        self.client.force_login(self.user)
        self.imovel = Imovel.objects.create(
            user=self.user,
            endereco="Rua Financeira 100",
            cidade="Salvador",
            estado="BA",
            etapa="registro_desocupacao",
            lance=100000,
            avaliacao=150000,
            preco_venda=190000,
        )

    def test_cria_edita_e_exclui_categoria_financeira(self):
        response = self.client.post(
            reverse("criar_categoria_financeira"),
            {"nome": "Reforma", "tipo": "despesa", "icone": "$"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        data = response.json()
        categoria = CategoriaFinanceira.objects.get(pk=data["categoria"]["id"])

        self.assertEqual(response.status_code, 201)
        self.assertEqual(categoria.nome, "Reforma")

        response = self.client.post(
            reverse("editar_categoria_financeira", args=[categoria.pk]),
            {"nome": "Reforma pesada", "tipo": "despesa", "icone": "R"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        categoria.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(categoria.nome, "Reforma pesada")

        response = self.client.post(
            reverse("excluir_categoria_financeira", args=[categoria.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CategoriaFinanceira.objects.filter(pk=categoria.pk).exists())

    def test_form_lancamento_renderiza_painel_moderno(self):
        response = self.client.get(reverse("novo_lancamento"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lançamento financeiro")
        self.assertContains(response, "Selecionar ou criar categoria")

    def test_novo_lancamento_usa_categoria_e_valor_br(self):
        categoria = CategoriaFinanceira.objects.create(nome="Condomínio", tipo="despesa", icone="$")

        response = self.client.post(
            reverse("novo_lancamento"),
            {
                "imovel": str(self.imovel.pk),
                "categoria": str(categoria.pk),
                "tipo": "despesa",
                "descricao": "Taxa condominial",
                "valor": "1.250,75",
                "data": "2026-06-05",
                "status": "confirmado",
                "obs": "Pago no boleto.",
            },
        )

        lancamento = LancamentoFinanceiro.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(lancamento.user, self.user)
        self.assertEqual(lancamento.imovel, self.imovel)
        self.assertEqual(lancamento.categoria, categoria)
        self.assertEqual(lancamento.valor, Decimal("1250.75"))
