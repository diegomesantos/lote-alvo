from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from apps.calculadora.models import (
    CartorioFaixa,
    CartorioFonteEvento,
    CartorioFonteMonitorada,
    CartorioRegraExtra,
    CartorioTabela,
)
from apps.calculadora.services.cartorio_fontes import verificar_fonte_cartorio
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


class FakeFonteResponse:
    def __init__(self, content=b"<html>ok</html>", status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html"}

    def iter_content(self, chunk_size=65536):
        yield self.content


class FakeFonteSession:
    def __init__(self, *responses):
        self.responses = list(responses)

    def get(self, *args, **kwargs):
        if not self.responses:
            return FakeFonteResponse()
        return self.responses.pop(0)


class CartorioFonteMonitoramentoTests(TestCase):
    def criar_fonte(self):
        return CartorioFonteMonitorada.objects.create(
            uf="BA",
            nome="TJ-BA",
            url="https://example.com/cartorio-ba",
            ativa=True,
        )

    def test_primeira_coleta_grava_hash_sem_evento_pendente(self):
        fonte = self.criar_fonte()

        resultado = verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(FakeFonteResponse(b"<html><body>Tabela 2026</body></html>")),
        )

        fonte.refresh_from_db()
        self.assertEqual(resultado["status"], "sem_mudanca")
        self.assertTrue(fonte.ultimo_hash)
        self.assertEqual(CartorioFonteEvento.objects.count(), 0)

    def test_mudanca_na_fonte_cria_evento_pendente(self):
        fonte = self.criar_fonte()
        tabela = CartorioTabela.objects.create(
            uf="BA",
            ano=date.today().year,
            tipo=CartorioTabela.TIPO_REGISTRO,
            vigente_inicio=date(date.today().year, 1, 1),
            fonte_nome="TJ-BA",
            fonte_url=fonte.url,
            status=CartorioTabela.STATUS_VALIDADA,
            ativo=True,
        )
        extra = CartorioRegraExtra.objects.create(
            uf="BA",
            ano=date.today().year,
            nome="Fundo teste",
            percentual=Decimal("0.1000"),
            vigente_inicio=date(date.today().year, 1, 1),
            fonte_nome="TJ-BA",
            fonte_url=fonte.url,
            status=CartorioRegraExtra.STATUS_VALIDADA,
            ativo=True,
        )
        verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(FakeFonteResponse(b"<html><body>Tabela 2026</body></html>")),
        )
        fonte.refresh_from_db()

        resultado = verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(FakeFonteResponse(b"<html><body>Tabela 2027 atualizada</body></html>")),
        )

        evento = CartorioFonteEvento.objects.get()
        tabela.refresh_from_db()
        extra.refresh_from_db()
        self.assertEqual(resultado["status"], "alterada")
        self.assertEqual(evento.status, CartorioFonteEvento.STATUS_PENDENTE)
        self.assertEqual(evento.tipo, CartorioFonteEvento.TIPO_MUDANCA)
        self.assertTrue(evento.aplicacao_automatica)
        self.assertEqual(evento.tabelas_afetadas, 1)
        self.assertEqual(evento.extras_afetados, 1)
        self.assertEqual(tabela.status, CartorioTabela.STATUS_PENDENTE)
        self.assertEqual(extra.status, CartorioRegraExtra.STATUS_PENDENTE)
        self.assertIn("revalidacao manual", tabela.observacoes)
        self.assertIn("Revisar tabela", evento.mensagem)

    def test_erro_na_fonte_cria_evento_pendente(self):
        fonte = self.criar_fonte()

        resultado = verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(FakeFonteResponse(status_code=500)),
        )

        evento = CartorioFonteEvento.objects.get()
        fonte.refresh_from_db()
        self.assertEqual(resultado["status"], "erro")
        self.assertEqual(evento.status, CartorioFonteEvento.STATUS_PENDENTE)
        self.assertEqual(evento.tipo, CartorioFonteEvento.TIPO_ERRO)
        self.assertIn("HTTP 500", fonte.ultimo_erro)

    def test_seed_cria_fontes_monitoradas_conhecidas(self):
        call_command("seed_cartorio_tabelas", "--uf", "BA")

        fonte = CartorioFonteMonitorada.objects.get(uf="BA")
        self.assertIn("tjba", fonte.url)
        self.assertTrue(fonte.ativa)
