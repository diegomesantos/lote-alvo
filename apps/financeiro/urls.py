from django.urls import path
from . import views

urlpatterns = [
    path("",                          views.dashboard,          name="financeiro"),
    path("lancamento/novo/",          views.novo_lancamento,    name="novo_lancamento"),
    path("lancamento/<int:pk>/editar/",views.editar_lancamento, name="editar_lancamento"),
    path("lancamento/<int:pk>/excluir/",views.excluir_lancamento,name="excluir_lancamento"),
]
