from django.urls import path
from . import views

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("login/", views.entrar, name="entrar"),
    path("logout/", views.sair, name="sair"),
    path("perfil/", views.perfil, name="perfil"),
]
