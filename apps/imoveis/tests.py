import shutil
import tempfile
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CHECKLIST_PADRAO, Imovel, ImovelArquivo, ImovelChecklistItem, ImovelComentario


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="imoveis-test-media-")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ImovelInteracaoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username="investidor",
            email="investidor@example.com",
            password="senha123",
        )
        self.client.force_login(self.user)
        self.imovel = Imovel.objects.create(
            user=self.user,
            endereco="Rua Teste 123",
            cidade="Salvador",
            estado="BA",
            lance=100000,
            avaliacao=150000,
            preco_venda=180000,
        )

    def test_detalhe_cria_checklist_padrao(self):
        response = self.client.get(reverse("detalhe", args=[self.imovel.pk]))

        total_padrao = sum(len(itens) for itens in CHECKLIST_PADRAO.values())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ImovelChecklistItem.objects.filter(imovel=self.imovel).count(), total_padrao)
        self.assertContains(response, "Checklist do ciclo do leilão")
        self.assertContains(response, "Triagem Jurídica")
        self.assertContains(response, "Registro e Desocupação")

    def test_toggle_checklist_item_salva_estado(self):
        self.client.get(reverse("detalhe", args=[self.imovel.pk]))
        item = ImovelChecklistItem.objects.filter(imovel=self.imovel).first()

        response = self.client.post(
            reverse("toggle_checklist_item", args=[self.imovel.pk, item.pk]),
            {"concluido": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        item.refresh_from_db()
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertTrue(item.concluido)
        self.assertEqual(data["total_concluido"], 1)

    def test_fluxos_de_interacao_manual(self):
        self.client.get(reverse("detalhe", args=[self.imovel.pk]))

        response = self.client.post(
            reverse("adicionar_checklist_item", args=[self.imovel.pk]),
            {"etapa": "estoque", "texto": "Item criado pelo investidor"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ImovelChecklistItem.objects.filter(
                imovel=self.imovel,
                etapa="estoque",
                texto="Item criado pelo investidor",
            ).exists()
        )

        response = self.client.post(
            reverse("adicionar_comentario", args=[self.imovel.pk]),
            {"texto": "Comentário operacional"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ImovelComentario.objects.filter(imovel=self.imovel, texto="Comentário operacional").exists())

        arquivo = SimpleUploadedFile("apoio.txt", b"arquivo de apoio", content_type="text/plain")
        response = self.client.post(
            reverse("adicionar_arquivo", args=[self.imovel.pk]),
            {"arquivo": arquivo, "nome": "Apoio", "categoria": "apoio"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ImovelArquivo.objects.filter(imovel=self.imovel, nome="Apoio").exists())

        foto = SimpleUploadedFile(
            "foto.gif",
            (
                b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
                b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
                b"\x00\x00\x02\x02D\x01\x00;"
            ),
            content_type="image/gif",
        )
        response = self.client.post(
            reverse("atualizar_identidade", args=[self.imovel.pk]),
            {"titulo_personalizado": "Título do investidor", "foto": foto},
        )
        self.imovel.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.imovel.titulo_card, "Título do investidor")
        self.assertTrue(self.imovel.foto)

    def test_financeiro_express_atualiza_premissas(self):
        response = self.client.post(
            reverse("atualizar_financeiro_express", args=[self.imovel.pk]),
            {
                "avaliacao": "210.000,00",
                "lance": "120.000,50",
                "preco_venda": "240.000,00",
                "rec_aluguel_am": "1.500,00",
                "giro_padrao": "6",
                "tipo_pgto": "Financiamento SAC",
                "entrada": "35,00",
                "prazo_fin": "240",
                "cet_aa": "11,50",
                "reformas": "20.000,00",
                "custo_desocup": "8.000,00",
                "debitos": "3.000,00",
                "despesas_div": "1.000,00",
                "iptu_am": "250,00",
                "cond_am": "600,00",
                "pct_leiloeiro": "5,00",
                "pct_corretor": "6,00",
                "av_fiscal": "130.000,00",
                "pct_itbi_base": "Avaliação Fiscal",
                "aliq_itbi": "3,00",
                "lucro_minimo": "30.000,00",
                "incremento_lance": "2.500,00",
            },
        )

        self.imovel.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.imovel.lance, Decimal("120000.50"))
        self.assertEqual(self.imovel.preco_venda, Decimal("240000.00"))
        self.assertEqual(self.imovel.giro_padrao, 6)
        self.assertEqual(self.imovel.tipo_pgto, "Financiamento SAC")
        self.assertEqual(self.imovel.pct_itbi_base, "Avaliação Fiscal")
        self.assertEqual(self.imovel.cond_am, Decimal("600.00"))

    def test_arrastar_para_arrematado_inicia_pos_arrematacao(self):
        response = self.client.post(
            reverse("atualizar_etapa", args=[self.imovel.pk]),
            {"etapa": "registro_desocupacao"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.imovel.refresh_from_db()
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(self.imovel.etapa, "registro_desocupacao")
        self.assertEqual(data["fase"], "pos")
