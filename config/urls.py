from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/kanban/", permanent=False)),
    path("accounts/", include("apps.accounts.urls")),
    path("kanban/", include("apps.imoveis.urls")),
    path("calculadora/", include("apps.calculadora.urls")),
    path("financeiro/", include("apps.financeiro.urls")),
    path("leiloes/", include("apps.leiloes.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
