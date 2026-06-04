from django.urls import path
from . import views

app_name = 'leiloes'

urlpatterns = [
    path('', views.explorador_leiloes, name='explorador'),
    path('imagem/<str:imovel_id>/', views.imagem_imovel_caixa, name='imagem'),
    path('api/cidades/', views.api_cidades_por_estado, name='api_cidades'),
    path('api/imovel/<str:imovel_id>/', views.api_imovel_detail, name='api_imovel_detail'),
    path('sync/', views.sincronizar_view, name='sincronizar'),
    path('cadastrar/<str:imovel_id>/', views.cadastrar_em_meus_imoveis, name='cadastrar_meus_imoveis'),
    path('analise-juridica/<str:imovel_id>/', views.gerar_analise_juridica_ia, name='gerar_analise_juridica'),
    path('<str:imovel_id>/', views.detalhe_imovel, name='detalhe'),
]
