import shutil
import tempfile
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    CHECKLIST_PADRAO,
    Imovel,
    ImovelArquivo,
    ImovelChecklistItem,
    ImovelComentario,
    ImovelCompartilhamento,
    NotificacaoUsuario,
)


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="imoveis-test-media-")
TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, STORAGES=TEST_STORAGES)
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
        self.leitor = User.objects.create_user(
            username="leitor",
            email="leitor@example.com",
            password="senha123",
        )
        self.editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
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

    def test_imovel_avulso_com_matricula_e_edital_anexados_marca_documentos_completo(self):
        ImovelArquivo.objects.create(
            imovel=self.imovel,
            nome="Matrícula",
            categoria="matricula",
            arquivo=SimpleUploadedFile("matricula.pdf", b"pdf-matricula", content_type="application/pdf"),
            enviado_por=self.user,
        )
        ImovelArquivo.objects.create(
            imovel=self.imovel,
            nome="Edital",
            categoria="edital",
            arquivo=SimpleUploadedFile("edital.pdf", b"pdf-edital", content_type="application/pdf"),
            enviado_por=self.user,
        )

        response = self.client.get(reverse("detalhe", args=[self.imovel.pk]))

        indicador_documentos = next(
            item for item in response.context["indicadores_decisao"]
            if item["titulo"] == "Documentos"
        )
        documentos = response.context["documentos"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(indicador_documentos["valor"], "Completo")
        self.assertTrue(all(documento["disponivel"] for documento in documentos))
        self.assertEqual({documento["origem"] for documento in documentos}, {"Arquivo anexado"})

    def test_modal_calculo_atualiza_premissas(self):
        response = self.client.post(
            reverse("atualizar_dados_calculo", args=[self.imovel.pk]),
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
                "aliq_itbi_fin": "1,50",
                "modo_cartorio": "Automático",
                "escritura_manual": "0,00",
                "registro_manual": "0,00",
                "laudemio_pct": "0,00",
                "custo_oport_aa": "10,00",
                "tipo_pessoa": "Pessoa Física",
                "meses_titulo": "2",
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

    def test_arquivar_remove_card_do_kanban(self):
        response = self.client.post(
            reverse("atualizar_etapa", args=[self.imovel.pk]),
            {"etapa": "arquivado", "motivo_arquivamento": "sem_interesse"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.imovel.refresh_from_db()
        kanban = self.client.get(reverse("kanban"))
        data = response.json()
        titulos_ativos = [
            card["imovel"].titulo_card
            for coluna in list(kanban.context["colunas_pre"]) + list(kanban.context["colunas_pos"])
            for card in coluna["cards"]
        ]
        titulos_arquivados = [card["imovel"].titulo_card for card in kanban.context["cards_arquivados"]]

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(self.imovel.etapa, "arquivado")
        self.assertEqual(self.imovel.motivo_arquivamento, "sem_interesse")
        self.assertIsNotNone(self.imovel.arquivado_em)
        self.assertNotIn(self.imovel.titulo_card, titulos_ativos)
        self.assertIn(self.imovel.titulo_card, titulos_arquivados)

    def test_desarquivar_limpa_metadados_e_retorna_para_etapa_ativa(self):
        self.client.post(
            reverse("atualizar_etapa", args=[self.imovel.pk]),
            {"etapa": "arquivado", "motivo_arquivamento": "aguardar"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        response = self.client.post(
            reverse("atualizar_etapa", args=[self.imovel.pk]),
            {"etapa": "triagem_financeira"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.imovel.refresh_from_db()
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(self.imovel.etapa, "triagem_financeira")
        self.assertIsNone(self.imovel.arquivado_em)
        self.assertEqual(self.imovel.motivo_arquivamento, "")

    def test_lista_filtra_ativos_arquivados_e_todos(self):
        arquivado = Imovel.objects.create(
            user=self.user,
            endereco="Rua Arquivada 456",
            cidade="Salvador",
            estado="BA",
            etapa="arquivado",
            arquivado_em=timezone.now(),
            motivo_arquivamento="leilao_encerrado",
            lance=90000,
            avaliacao=140000,
            preco_venda=170000,
        )

        ativos = self.client.get(reverse("listar"))
        arquivados = self.client.get(f"{reverse('listar')}?status=arquivados")
        todos = self.client.get(f"{reverse('listar')}?status=todos")

        ativos_ids = {str(card["imovel"].pk) for card in ativos.context["cards"]}
        arquivados_ids = {str(card["imovel"].pk) for card in arquivados.context["cards"]}
        todos_ids = {str(card["imovel"].pk) for card in todos.context["cards"]}

        self.assertEqual(ativos.context["status"], "ativos")
        self.assertIn(str(self.imovel.pk), ativos_ids)
        self.assertNotIn(str(arquivado.pk), ativos_ids)
        self.assertEqual(arquivados.context["status"], "arquivados")
        self.assertNotIn(str(self.imovel.pk), arquivados_ids)
        self.assertIn(str(arquivado.pk), arquivados_ids)
        self.assertEqual(todos.context["status"], "todos")
        self.assertIn(str(self.imovel.pk), todos_ids)
        self.assertIn(str(arquivado.pk), todos_ids)

    def test_excluir_ajax_remove_card(self):
        response = self.client.post(
            reverse("excluir", args=[self.imovel.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertFalse(Imovel.objects.filter(pk=self.imovel.pk).exists())
        self.assertEqual(data["deleted_id"], str(self.imovel.pk))

    def test_proprietario_compartilha_e_remove_acesso(self):
        response = self.client.post(
            reverse("compartilhar_imovel", args=[self.imovel.pk]),
            {"user_id": self.leitor.pk, "permissao": "leitura"},
        )

        self.assertEqual(response.status_code, 302)
        compartilhamento = ImovelCompartilhamento.objects.get(imovel=self.imovel, user=self.leitor)
        notificacao = NotificacaoUsuario.objects.get(user=self.leitor, imovel=self.imovel)
        self.assertEqual(compartilhamento.permissao, "leitura")
        self.assertTrue(compartilhamento.ativo)
        self.assertEqual(compartilhamento.criado_por, self.user)
        self.assertEqual(notificacao.tipo, "compartilhamento")
        self.assertIsNone(notificacao.lida_em)
        self.assertIn("compartilhou", notificacao.mensagem)

        self.client.force_login(self.leitor)
        detalhe = self.client.get(reverse("detalhe", args=[self.imovel.pk]))
        lista = self.client.get(f"{reverse('listar')}?status=compartilhados")

        self.assertEqual(detalhe.status_code, 200)
        self.assertFalse(detalhe.context["acesso"]["can_edit"])
        self.assertTrue(detalhe.context["acesso"]["is_shared"])
        self.assertEqual(detalhe.context["notificacoes_nao_lidas_count"], 1)
        self.assertIn(str(self.imovel.pk), {str(card["imovel"].pk) for card in lista.context["cards"]})

        self.client.force_login(self.user)
        response = self.client.post(
            reverse("remover_compartilhamento", args=[self.imovel.pk, compartilhamento.pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ImovelCompartilhamento.objects.filter(pk=compartilhamento.pk).exists())
        self.assertEqual(NotificacaoUsuario.objects.filter(user=self.leitor, imovel=self.imovel, lida_em__isnull=True).count(), 0)

        self.client.force_login(self.leitor)
        response = self.client.get(reverse("detalhe", args=[self.imovel.pk]))
        self.assertEqual(response.status_code, 404)

    def test_usuario_com_leitura_nao_altera_card_compartilhado(self):
        ImovelCompartilhamento.objects.create(
            imovel=self.imovel,
            user=self.leitor,
            permissao="leitura",
            criado_por=self.user,
        )

        self.client.force_login(self.leitor)
        mover = self.client.post(
            reverse("atualizar_etapa", args=[self.imovel.pk]),
            {"etapa": "triagem_financeira"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        excluir = self.client.post(
            reverse("excluir", args=[self.imovel.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.imovel.refresh_from_db()
        self.assertEqual(mover.status_code, 404)
        self.assertEqual(excluir.status_code, 404)
        self.assertEqual(self.imovel.etapa, "estoque")

    def test_usuario_com_edicao_altera_mas_nao_exclui_card_compartilhado(self):
        ImovelCompartilhamento.objects.create(
            imovel=self.imovel,
            user=self.editor,
            permissao="edicao",
            criado_por=self.user,
        )

        self.client.force_login(self.editor)
        mover = self.client.post(
            reverse("atualizar_etapa", args=[self.imovel.pk]),
            {"etapa": "triagem_financeira"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        excluir = self.client.post(
            reverse("excluir", args=[self.imovel.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        compartilhar = self.client.post(
            reverse("compartilhar_imovel", args=[self.imovel.pk]),
            {"user_id": self.leitor.pk, "permissao": "leitura"},
        )

        self.imovel.refresh_from_db()
        self.assertEqual(mover.status_code, 200)
        self.assertEqual(excluir.status_code, 404)
        self.assertEqual(compartilhar.status_code, 404)
        self.assertEqual(self.imovel.etapa, "triagem_financeira")
        self.assertTrue(Imovel.objects.filter(pk=self.imovel.pk).exists())
        self.assertFalse(ImovelCompartilhamento.objects.filter(imovel=self.imovel, user=self.leitor).exists())

    def test_abrir_notificacao_marca_como_lida_e_redireciona(self):
        notificacao = NotificacaoUsuario.objects.create(
            user=self.leitor,
            tipo="compartilhamento",
            titulo="Imóvel compartilhado com você",
            mensagem="Teste",
            url=reverse("detalhe", args=[self.imovel.pk]),
            imovel=self.imovel,
            criado_por=self.user,
        )
        ImovelCompartilhamento.objects.create(
            imovel=self.imovel,
            user=self.leitor,
            permissao="leitura",
            criado_por=self.user,
        )

        self.client.force_login(self.leitor)
        response = self.client.get(reverse("abrir_notificacao", args=[notificacao.pk]))

        notificacao.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("detalhe", args=[self.imovel.pk]))
        self.assertIsNotNone(notificacao.lida_em)

    def test_marcar_todas_notificacoes_como_lidas(self):
        NotificacaoUsuario.objects.create(
            user=self.leitor,
            tipo="compartilhamento",
            titulo="Aviso 1",
            mensagem="Teste",
            url=reverse("kanban"),
            imovel=self.imovel,
            criado_por=self.user,
        )
        NotificacaoUsuario.objects.create(
            user=self.leitor,
            tipo="compartilhamento",
            titulo="Aviso 2",
            mensagem="Teste",
            url=reverse("kanban"),
            imovel=self.imovel,
            criado_por=self.user,
        )

        self.client.force_login(self.leitor)
        response = self.client.post(
            reverse("marcar_notificacoes_lidas"),
            {"next": reverse("kanban")},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(NotificacaoUsuario.objects.filter(user=self.leitor, lida_em__isnull=True).count(), 0)
