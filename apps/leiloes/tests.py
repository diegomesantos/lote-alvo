from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from bs4 import BeautifulSoup

from .analise_juridica import (
    _erro_documento_nao_pdf,
    _pagina_precisa_ocr,
)
from .caixa_csv import (
    ImovelCaixaIndisponivelError,
    extrair_detalhes_html,
    extrair_fotos,
    filtrar_detalhe_pendente,
)
from .models import ImovelCaixa
from .regras_despesas import extrair_regras_despesas


class ExploradorLeiloesFiltroBairroTests(TestCase):
    def setUp(self):
        self.url = reverse("leiloes:explorador")
        self.centro = self._imovel("CAIXA-1", "Centro")
        self.barra = self._imovel("CAIXA-2", "Barra")
        self.pituba = self._imovel("CAIXA-3", "Pituba")

    def _imovel(self, imovel_id, bairro):
        return ImovelCaixa.objects.create(
            imovel_id_caixa=imovel_id,
            endereco=f"Rua Teste, {imovel_id}",
            cidade="Salvador",
            estado="BA",
            bairro=bairro,
            tipo="apto",
            valor_avaliacao=Decimal("300000.00"),
            percentual_desconto=Decimal("20.00"),
            valor_minimo_lance=Decimal("240000.00"),
            tipo_leilao="extra",
            formas_pagamento={
                "financiamento": True,
                "fgts": False,
                "consorcio": False,
            },
        )

    def _ids_resultado(self, response):
        return {
            imovel.imovel_id_caixa
            for imovel in response.context["page_obj"].object_list
        }

    def test_bairro_sem_modo_explicitado_usa_inclusao_por_compatibilidade(self):
        response = self.client.get(self.url, {"bairros": ["Centro"]})

        self.assertEqual(response.context["filtros_ativos"]["bairro_mode"], "include")
        self.assertEqual(self._ids_resultado(response), {self.centro.imovel_id_caixa})

    def test_bairro_modo_exclude_remove_bairros_selecionados(self):
        response = self.client.get(
            self.url,
            {"bairro_mode": "exclude", "bairros": ["Centro"]},
        )

        self.assertEqual(response.context["filtros_ativos"]["bairro_mode"], "exclude")
        self.assertEqual(
            self._ids_resultado(response),
            {self.barra.imovel_id_caixa, self.pituba.imovel_id_caixa},
        )

    def test_bairro_modo_all_ignora_bairros_residuais_da_url(self):
        response = self.client.get(
            self.url,
            {"bairro_mode": "all", "bairros": ["Centro"]},
        )

        self.assertEqual(response.context["filtros_ativos"]["bairro_mode"], "all")
        self.assertEqual(response.context["filtros_ativos"]["bairros"], [])
        self.assertEqual(
            self._ids_resultado(response),
            {
                self.centro.imovel_id_caixa,
                self.barra.imovel_id_caixa,
                self.pituba.imovel_id_caixa,
            },
        )


class RegrasDespesasParserTests(TestCase):
    def test_classifica_limite_condominio_e_tributo_integral_comprador(self):
        regras = extrair_regras_despesas(
            "Condomínio: Sob responsabilidade do comprador, até o limite de "
            "10% em relação ao valor de avaliação do imóvel. A CAIXA realizará "
            "o pagamento apenas do valor que exceder o limite de 10%. "
            "Tributos: Sob responsabilidade do comprador."
        )

        self.assertEqual(regras["despesa_condominio"], "comprador_ate_10")
        self.assertEqual(regras["despesa_tributos"], "comprador")

    def test_classifica_redacao_inferior_superior_a_dez_por_cento(self):
        regras = extrair_regras_despesas(
            "Condomínio: Sob responsabilidade do comprador, até o limite de 10%. "
            "A CAIXA paga o excedente. Tributos: Sob responsabilidade do comprador, "
            "quando o débito for inferior a 10% do valor de avaliação. A CAIXA "
            "paga integralmente quando o débito for superior a 10%."
        )

        self.assertEqual(regras["despesa_condominio"], "comprador_ate_10")
        self.assertEqual(regras["despesa_tributos"], "comprador_ate_10")

    def test_classifica_regra_combinada_quitada_pela_caixa(self):
        regras = extrair_regras_despesas(
            "Tributos e condomínio: A CAIXA pagará integralmente. "
            "Corretores credenciados Regras da Venda Online"
        )

        self.assertEqual(regras["despesa_condominio"], "caixa")
        self.assertEqual(regras["despesa_tributos"], "caixa")

    def test_retorna_indeterminado_sem_texto_de_regras(self):
        regras = extrair_regras_despesas("Imóvel sem informação sobre despesas.")

        self.assertEqual(regras["despesa_condominio"], "indeterminado")
        self.assertEqual(regras["despesa_tributos"], "indeterminado")


class ExploradorLeiloesFiltroDespesasTests(TestCase):
    def setUp(self):
        self.url = reverse("leiloes:explorador")
        base = {
            "endereco": "Rua Teste",
            "cidade": "Salvador",
            "estado": "BA",
            "tipo": "apto",
            "valor_avaliacao": Decimal("300000.00"),
            "percentual_desconto": Decimal("20.00"),
            "valor_minimo_lance": Decimal("240000.00"),
            "tipo_leilao": "extra",
        }
        self.limite = ImovelCaixa.objects.create(
            imovel_id_caixa="DESP-1",
            despesa_condominio="comprador_ate_10",
            despesa_tributos="comprador",
            **base,
        )
        self.caixa = ImovelCaixa.objects.create(
            imovel_id_caixa="DESP-2",
            despesa_condominio="caixa",
            despesa_tributos="caixa",
            **base,
        )

    def test_filtra_condominio_ate_dez_por_cento(self):
        response = self.client.get(
            self.url,
            {"despesa_condominio": ["comprador_ate_10"]},
        )

        ids = {
            imovel.imovel_id_caixa
            for imovel in response.context["page_obj"].object_list
        }
        self.assertEqual(ids, {self.limite.imovel_id_caixa})

    def test_multiselecao_de_despesas_usa_ou_no_mesmo_campo(self):
        response = self.client.get(
            self.url,
            {"despesa_condominio": ["comprador_ate_10", "caixa"]},
        )

        ids = {
            imovel.imovel_id_caixa
            for imovel in response.context["page_obj"].object_list
        }
        self.assertEqual(ids, {self.limite.imovel_id_caixa, self.caixa.imovel_id_caixa})

    def test_opcoes_exibem_todas_as_regras_e_desabilitam_as_sem_resultado(self):
        response = self.client.get(self.url)

        opcoes_condominio = {
            opcao["value"]: opcao
            for opcao in response.context["despesas_condominio_opcoes"]
        }
        self.assertEqual(
            list(opcoes_condominio),
            ["comprador", "comprador_ate_10", "caixa"],
        )
        self.assertEqual(opcoes_condominio["comprador"]["total"], 0)
        self.assertTrue(opcoes_condominio["comprador"]["disabled"])
        self.assertEqual(opcoes_condominio["caixa"]["total"], 1)
        self.assertFalse(opcoes_condominio["caixa"]["disabled"])


class ExtracaoFotosTests(TestCase):
    def test_extrai_fotos_de_atributos_e_scripts(self):
        soup = BeautifulSoup(
            """
            <html>
              <body>
                <img data-src="/fotos/F12321.jpg" />
                <script>
                  const galeria = ["/fotos/F12322.jpg"];
                </script>
              </body>
            </html>
            """,
            "html.parser",
        )

        fotos = extrair_fotos(soup)

        self.assertEqual(
            fotos,
            [
                "https://venda-imoveis.caixa.gov.br/fotos/F12321.jpg",
                "https://venda-imoveis.caixa.gov.br/fotos/F12322.jpg",
            ],
        )


class ExtracaoDetalhesIndisponiveisTests(TestCase):
    def test_nao_salva_como_detalhe_valido_quando_caixa_informa_indisponivel(self):
        html = """
        <html>
          <body>
            <main>
              Ocorreu um erro ao tentar recuperar os dados do imóvel.
              O imóvel que você procura não está mais disponível para venda.
            </main>
          </body>
        </html>
        """

        with self.assertRaises(ImovelCaixaIndisponivelError):
            extrair_detalhes_html(html, url="https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp")

    def test_fila_reprocessa_detalhe_antigo_com_pagina_indisponivel(self):
        imovel = ImovelCaixa.objects.create(
            imovel_id_caixa="INDISP-1",
            endereco="Rua Teste",
            cidade="Salvador",
            estado="BA",
            tipo="apto",
            valor_avaliacao=Decimal("300000.00"),
            percentual_desconto=Decimal("20.00"),
            valor_minimo_lance=Decimal("240000.00"),
            tipo_leilao="extra",
            detalhe_atualizado_em=timezone.now(),
            detalhes={
                "detalhe_caixa": {
                    "texto_extraido": (
                        "Topo Ocorreu um erro ao tentar recuperar os dados do imóvel. "
                        "O imóvel que você procura não está mais disponível para venda."
                    )
                }
            },
        )

        ids = {
            item.imovel_id_caixa
            for item in filtrar_detalhe_pendente(ImovelCaixa.objects.all())
        }

        self.assertIn(imovel.imovel_id_caixa, ids)


class ImagemImovelCaixaTests(TestCase):
    def setUp(self):
        self.imovel = ImovelCaixa.objects.create(
            imovel_id_caixa="IMG-1",
            endereco="Rua Teste, 1",
            cidade="Salvador",
            estado="BA",
            tipo="apto",
            valor_avaliacao=Decimal("300000.00"),
            percentual_desconto=Decimal("20.00"),
            valor_minimo_lance=Decimal("240000.00"),
            tipo_leilao="extra",
            link_caixa="https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?imovel=IMG-1",
            foto_url="https://venda-imoveis.caixa.gov.br/fotos/FIMG-121.jpg",
        )

    @patch("apps.leiloes.views.requests.get")
    def test_tenta_fallback_22_e_salva_url_valida(self, mock_get):
        resposta_404 = Mock()
        resposta_404.status_code = 404
        resposta_404.headers = {"content-type": "text/html"}
        resposta_404.close = Mock()

        resposta_200 = Mock()
        resposta_200.status_code = 200
        resposta_200.headers = {
            "content-type": "image/jpeg",
            "content-length": "3",
        }
        resposta_200.iter_content = Mock(return_value=iter([b"abc"]))
        resposta_200.close = Mock()

        mock_get.side_effect = [resposta_404, resposta_200]

        response = self.client.get(reverse("leiloes:imagem", args=[self.imovel.imovel_id_caixa]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(b"".join(response.streaming_content), b"abc")
        self.imovel.refresh_from_db()
        self.assertEqual(
            self.imovel.foto_url,
            "https://venda-imoveis.caixa.gov.br/fotos/FIMG-122.jpg",
        )
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(
            mock_get.call_args_list[0].args[0],
            "https://venda-imoveis.caixa.gov.br/fotos/FIMG-121.jpg",
        )
        self.assertEqual(mock_get.call_args_list[1].args[0], "https://venda-imoveis.caixa.gov.br/fotos/FIMG-122.jpg")


class AnaliseJuridicaExtracaoTests(TestCase):
    def test_pagina_com_apenas_autenticacao_precisa_ocr(self):
        texto = (
            "Pedido de Certidao numero 123. Documento assinado no Assinador ONR. "
            "Para validar o documento e suas assinaturas acesse o portal de validacao. "
            "Codigo de validacao ABCD-EFGH. Selo de autenticidade informado. "
        )

        self.assertTrue(_pagina_precisa_ocr(texto))

    def test_pagina_com_atos_registrais_nao_forca_ocr(self):
        texto = (
            "CERTIDAO DE INTEIRO TEOR MATRICULA 9740. "
            "R-1 alienacao fiduciaria em favor da Caixa Economica Federal. "
            "AV-2 consolidacao da propriedade. "
            "R-3 credor fiduciario e devedor fiduciante qualificados. "
            "AV-4 averbacao de leilao negativo e onus relacionados."
        )

        self.assertFalse(_pagina_precisa_ocr(texto))

    def test_erro_documento_nao_pdf_identifica_captcha(self):
        erro = _erro_documento_nao_pdf(
            b"<head><title>Radware Bot Manager CAPTCHA</title></head>",
            "text/html; charset=UTF-8",
        )

        self.assertIn("CAPTCHA", erro)
