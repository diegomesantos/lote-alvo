from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .analise_juridica import (
    _erro_documento_nao_pdf,
    _pagina_precisa_ocr,
)
from .models import ImovelCaixa


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
