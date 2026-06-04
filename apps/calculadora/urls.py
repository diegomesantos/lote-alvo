from django.urls import path
from . import views

urlpatterns = [
    path("",               views.index,              name="calculadora"),
    path("calcular/",      views.calcular_htmx,      name="calcular_htmx"),
    path("tabela-lances/", views.tabela_lances_view, name="tabela_lances"),
]
