from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.calculadora.models import CartorioFaixa, CartorioRegraExtra, CartorioTabela
from core.calculos.cartorio import calcular_cartorio, obter_tabelas_cartorio


class CartorioCalculoTests(TestCase):
    def criar_tabela(self, *, uf="BA", tipo="registro", valor="20.00", ano=None, fonte_nome="Fonte oficial"):
        ano = ano or date.today().year
        tabela = CartorioTabela.objects.create(
            uf=uf,
            ano=ano,
            tipo=tipo,
            vigente_inicio=date(ano, 1, 1),
            fonte_nome=fonte_nome,
            fonte_url="https://example.com/tabela",
            status=CartorioTabela.STATUS_VALIDADA,
            ativo=True,
        )
        CartorioFaixa.objects.create(
            tabela=tabela,
            ordem=1,
            limite_superior=Decimal("999999999.99"),
            valor=Decimal(valor),
        )
        return tabela

    def test_calculo_usa_tabela_legada_quando_banco_nao_tem_uf(self):
        resultado = calcular_cartorio("BA", 300000, "Extrajudicial")

        self.assertEqual(resultado["origem"], "codigo")
        self.assertGreater(resultado["total"], 0)
        self.assertEqual(resultado["fonte_status"], "legada")

    def test_calculo_prefere_tabela_versionada_do_banco(self):
        self.criar_tabela(tipo="escritura", valor="10.00")
        self.criar_tabela(tipo="registro", valor="20.00")
        CartorioRegraExtra.objects.create(
            uf="BA",
            ano=date.today().year,
            nome="Fundo teste",
            percentual=Decimal("1.5000"),
            vigente_inicio=date(date.today().year, 1, 1),
            fonte_nome="Fonte extra",
            fonte_url="https://example.com/extra",
            status=CartorioTabela.STATUS_VALIDADA,
            ativo=True,
        )

        resultado = calcular_cartorio("BA", 1000, "Extrajudicial")

        self.assertEqual(resultado["origem"], "banco")
        self.assertEqual(resultado["escritura"], 10.0)
        self.assertEqual(resultado["registro"], 20.0)
        self.assertEqual(resultado["extra"], 15.0)
        self.assertEqual(resultado["total"], 45.0)
        self.assertEqual(resultado["fonte_nome"], "Fonte oficial")
        self.assertEqual(resultado["fonte_status"], CartorioTabela.STATUS_VALIDADA)
        self.assertEqual(len(resultado["fontes"]), 3)

    def test_judicial_precisa_apenas_da_tabela_de_registro(self):
        self.criar_tabela(tipo="registro", valor="30.00")

        resultado = calcular_cartorio("BA", 1000, "Judicial")

        self.assertEqual(resultado["origem"], "banco")
        self.assertEqual(resultado["escritura"], 0)
        self.assertEqual(resultado["registro"], 30.0)
        self.assertEqual(resultado["total"], 30.0)

    def test_obter_tabelas_cartorio_expoe_tabelas_do_banco_para_template(self):
        self.criar_tabela(tipo="escritura", valor="11.00")
        self.criar_tabela(tipo="registro", valor="22.00")

        tabelas = obter_tabelas_cartorio("BA", "Extrajudicial")

        self.assertEqual(tabelas["origem"], "banco")
        self.assertEqual(tabelas["escritura"], [(999999999.99, 11.0)])
        self.assertEqual(tabelas["registro"], [(999999999.99, 22.0)])
