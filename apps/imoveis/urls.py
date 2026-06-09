from django.urls import path
from . import views

urlpatterns = [
    path("",              views.kanban,         name="kanban"),
    path("lista/",        views.listar,         name="listar"),
    path("novo/",         views.criar,          name="criar"),
    path("<uuid:pk>/",    views.detalhe,        name="detalhe"),
    path("<uuid:pk>/editar/", views.editar,     name="editar"),
    path("<uuid:pk>/excluir/", views.excluir,   name="excluir"),
    path("<uuid:pk>/etapa/",   views.atualizar_etapa, name="atualizar_etapa"),
    path("<uuid:pk>/dados-calculo/", views.atualizar_dados_calculo, name="atualizar_dados_calculo"),
    path("<uuid:pk>/identidade/", views.atualizar_identidade, name="atualizar_identidade"),
    path("<uuid:pk>/checklist/adicionar/", views.adicionar_checklist_item, name="adicionar_checklist_item"),
    path("<uuid:pk>/checklist/<int:item_id>/toggle/", views.toggle_checklist_item, name="toggle_checklist_item"),
    path("<uuid:pk>/arquivos/adicionar/", views.adicionar_arquivo, name="adicionar_arquivo"),
    path("<uuid:pk>/comentarios/adicionar/", views.adicionar_comentario, name="adicionar_comentario"),
    path("<uuid:pk>/tabela-lances/", views.tabela_lances_imovel, name="tabela_lances_imovel"),
    path("<uuid:pk>/simular-moradia/", views.simular_moradia_imovel, name="simular_moradia_imovel"),
    path("<uuid:pk>/analise-juridica/", views.gerar_analise_juridica_imovel, name="gerar_analise_juridica_imovel"),
    path("<uuid:pk>/analise-juridica/status/", views.analise_juridica_imovel_status, name="analise_juridica_imovel_status"),
    path("<uuid:pk>/arquivos/<int:arquivo_id>/excluir/", views.excluir_arquivo, name="excluir_arquivo"),
]
