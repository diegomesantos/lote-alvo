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


def _faixas_validas():
    return [
        (Decimal("1000"), Decimal("100")),
        (Decimal("2000"), Decimal("110")),
        (Decimal("3000"), Decimal("120")),
        (Decimal("4000"), Decimal("130")),
        (None, Decimal("150")),
    ]


class CartorioGuardasSanidadeTests(TestCase):
    def test_rejeita_poucas_faixas(self):
        from apps.calculadora.services.cartorio_parsers import validar_faixas

        ok, _ = validar_faixas([(Decimal("1000"), Decimal("10")), (None, Decimal("20"))])
        self.assertFalse(ok)

    def test_rejeita_valores_nao_crescentes(self):
        from apps.calculadora.services.cartorio_parsers import validar_faixas

        faixas = _faixas_validas()
        faixas[2] = (Decimal("3000"), Decimal("90"))  # quebra a monotonia
        ok, _ = validar_faixas(faixas)
        self.assertFalse(ok)

    def test_rejeita_valor_implausivel(self):
        from apps.calculadora.services.cartorio_parsers import validar_faixas

        faixas = _faixas_validas()
        faixas[-1] = (None, Decimal("9999999"))  # acima do teto plausível
        ok, _ = validar_faixas(faixas)
        self.assertFalse(ok)

    def test_rejeita_ultima_faixa_com_limite(self):
        from apps.calculadora.services.cartorio_parsers import validar_faixas

        faixas = _faixas_validas()
        faixas[-1] = (Decimal("5000"), Decimal("150"))  # última deveria ser None
        ok, _ = validar_faixas(faixas)
        self.assertFalse(ok)

    def test_aceita_faixas_boas(self):
        from apps.calculadora.services.cartorio_parsers import validar_faixas

        ok, motivo = validar_faixas(_faixas_validas())
        self.assertTrue(ok, motivo)


class CartorioAplicacaoTabelaTests(TestCase):
    def test_aplicar_tabela_cria_vigente_e_aposenta_anterior(self):
        from apps.calculadora.services.cartorio_parsers import aplicar_tabela

        antiga = CartorioTabela.objects.create(
            uf="BA",
            ano=date.today().year - 1,
            tipo=CartorioTabela.TIPO_REGISTRO,
            vigente_inicio=date(date.today().year - 1, 1, 1),
            fonte_nome="antiga",
            status=CartorioTabela.STATUS_VALIDADA,
            ativo=True,
        )

        nova = aplicar_tabela(
            "BA",
            "registro",
            _faixas_validas(),
            fonte_nome="auto",
            fonte_url="https://example.com/ba",
        )

        antiga.refresh_from_db()
        self.assertEqual(antiga.status, CartorioTabela.STATUS_SUBSTITUIDA)
        self.assertIsNotNone(antiga.vigente_fim)
        self.assertEqual(nova.status, CartorioTabela.STATUS_VALIDADA)
        self.assertEqual(nova.faixas.count(), 5)

        # o cálculo passa a usar a nova tabela vigente
        resultado = calcular_cartorio("BA", 1500, "Judicial")
        self.assertEqual(resultado["origem"], "banco")
        self.assertEqual(resultado["registro"], 110.0)

    def test_aplicar_tabela_rejeita_faixas_invalidas(self):
        from apps.calculadora.services.cartorio_parsers import (
            FaixasInvalidasError,
            aplicar_tabela,
        )

        faixas = [(Decimal("1000"), Decimal("100")), (None, Decimal("110"))]  # poucas
        with self.assertRaises(FaixasInvalidasError):
            aplicar_tabela("BA", "registro", faixas, fonte_nome="x", fonte_url="")


def _pdf_de_linhas(linhas):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 50
    for linha in linhas:
        page.insert_text((50, y), linha, fontsize=9)
        y += 11
    return doc.tobytes()


def _pdf_generico():
    """PDF 'faixa -> valor' em linha única (para o extrator genérico)."""
    return _pdf_de_linhas([
        "TABELA",
        "até R$ 1.000,00  R$ 100,00",
        "de 1.000,01 a R$ 2.000,00  R$ 110,00",
        "de 2.000,01 a R$ 3.000,00  R$ 120,00",
        "de 3.000,01 a R$ 4.000,00  R$ 130,00",
        "de 4.000,01 a R$ 5.000,00  R$ 140,00",
        "a partir de R$ 5.000,00  R$ 150,00",
    ])


def _ba_bloco(prefixo):
    """Bloco de tabela do TJ-BA (tokens em linhas separadas, com código do ato)."""
    linhas = ["VALOR A PAGAR (R$)", "Até", "1.600,00", "100,00", f"{prefixo}020"]
    faixas = [
        ("1.600,01", "3.200,00", "110,00", "030"),
        ("3.200,01", "8.000,00", "120,00", "040"),
        ("8.000,01", "12.000,00", "130,00", "049"),
        ("12.000,01", "16.000,00", "140,00", "058"),
    ]
    for lo, hi, val, suf in faixas:
        linhas += ["De", lo, "a", hi, val, f"{prefixo}{suf}"]
    linhas += ["A partir de", "16.000,01", "150,00", f"{prefixo}100"]
    return linhas


def _pdf_ba_estruturado():
    """PDF no formato real do TJ-BA: Item I (Notas, 01xxx) + Item VII (Reg, 07xxx)."""
    return _pdf_de_linhas(_ba_bloco("01") + _ba_bloco("07"))


class CartorioAplicacaoAutomaticaTests(TestCase):
    def test_extrator_pdf_generico_le_faixa_valor(self):
        from apps.calculadora.services.cartorio_parsers import extrair_faixas_pdf

        faixas = extrair_faixas_pdf(_pdf_generico())
        self.assertIsNotNone(faixas)
        self.assertEqual(faixas[0], (Decimal("1000"), Decimal("100")))
        self.assertIsNone(faixas[-1][0])  # última sem limite
        self.assertEqual(faixas[-1][1], Decimal("150"))

    def test_parsers_registrados_por_uf(self):
        from apps.calculadora.services.cartorio_parsers import PARSERS

        for uf in ("BA", "MG", "SC", "GO", "PE", "RS", "SP", "DF", "PR"):
            self.assertIn(uf, PARSERS)

    def test_df_extrai_faixa_total_em_uma_linha(self):
        from apps.calculadora.services.cartorio_parsers import _abrir_pdf, _df_tabela

        pdf = _pdf_de_linhas([
            "ATOS DOS NOTÁRIOS",
            "a até R$ 9.524,89 410,56 28,74 439,30",
            "b de R$ 9.524,90 a R$ 15.272,67 624,04 43,68 667,72",
            "c de R$ 15.272,68 a R$ 28.738,89 1.280,93 89,67 1.370,60",
            "d de R$ 28.738,90 a R$ 57.477,78 1.724,34 120,70 1.845,04",
            "e de R$ 57.477,79 a R$ 85.888,21 1.806,45 126,45 1.932,90",
            "f acima de R$ 85.888,21 1.888,56 132,20 2.020,76",
        ])
        faixas = _df_tabela(_abrir_pdf(pdf), [0], two_line=False)
        self.assertEqual(faixas[0], (Decimal("9524.89"), Decimal("439.30")))
        self.assertIsNone(faixas[-1][0])
        self.assertEqual(faixas[-1][1], Decimal("2020.76"))

    def test_parser_ba_separa_escritura_e_registro(self):
        from apps.calculadora.services.cartorio_parsers import parse_ba

        payload = {"bytes": _pdf_ba_estruturado(), "content_type": "application/pdf"}
        tabelas = parse_ba(payload, lambda url: None)
        self.assertIsNotNone(tabelas)
        self.assertEqual(tabelas["escritura"][0], (Decimal("1600"), Decimal("100")))
        self.assertIsNone(tabelas["registro"][-1][0])
        self.assertEqual(len(tabelas["registro"]), 6)

    def test_mudanca_para_pdf_aplica_tabela_automaticamente(self):
        fonte = CartorioFonteMonitorada.objects.create(
            uf="BA", nome="TJ-BA", url="https://example.com/cartorio-ba", ativa=True,
        )
        # 1ª coleta (HTML) só grava o hash
        verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(FakeFonteResponse(b"<html>tabela antiga</html>")),
        )
        fonte.refresh_from_db()

        # 2ª coleta: a fonte agora serve o PDF da tabela -> aplica automático
        resultado = verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(
                FakeFonteResponse(
                    _pdf_ba_estruturado(), headers={"content-type": "application/pdf"}
                )
            ),
        )

        self.assertEqual(resultado["status"], "alterada")
        self.assertTrue(resultado["aplicacao_automatica"])
        evento = CartorioFonteEvento.objects.get()
        self.assertTrue(evento.aplicacao_automatica)
        self.assertEqual(evento.status, CartorioFonteEvento.STATUS_REVISADO)

        # tabelas vigentes de escritura e registro foram criadas e validadas
        for tipo in (CartorioTabela.TIPO_ESCRITURA, CartorioTabela.TIPO_REGISTRO):
            tabela = CartorioTabela.objects.get(
                uf="BA", tipo=tipo, vigente_inicio=date.today()
            )
            self.assertEqual(tabela.status, CartorioTabela.STATUS_VALIDADA)
            self.assertEqual(tabela.faixas.count(), 6)

        resultado_calc = calcular_cartorio("BA", 1500, "Extrajudicial")
        self.assertEqual(resultado_calc["origem"], "banco")
        self.assertEqual(resultado_calc["registro"], 100.0)

    def test_pdf_quebrado_nao_aplica_e_cai_para_revisao(self):
        fonte = CartorioFonteMonitorada.objects.create(
            uf="BA", nome="TJ-BA", url="https://example.com/cartorio-ba", ativa=True,
        )
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
        verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(FakeFonteResponse(b"<html>antiga</html>")),
        )
        fonte.refresh_from_db()

        # PDF sem faixas reconhecíveis -> parser não retorna nada -> revisão manual
        import fitz

        doc = fitz.open()
        doc.new_page().insert_text((50, 60), "documento sem tabela de faixas", fontsize=10)
        resultado = verificar_fonte_cartorio(
            fonte,
            session=FakeFonteSession(
                FakeFonteResponse(doc.tobytes(), headers={"content-type": "application/pdf"})
            ),
        )

        tabela.refresh_from_db()
        self.assertEqual(resultado["status"], "alterada")
        self.assertFalse(resultado["aplicacao_automatica"])
        self.assertEqual(tabela.status, CartorioTabela.STATUS_PENDENTE)
