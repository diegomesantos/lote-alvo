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
    path("<uuid:pk>/tabela-lances/", views.tabela_lances_imovel, name="tabela_lances_imovel"),
]
