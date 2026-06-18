from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.static import serve
from core.views import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/kanban/", permanent=False)),
    path("accounts/", include("apps.accounts.urls")),
    path("kanban/", include("apps.imoveis.urls")),
    path("calculadora/", include("apps.calculadora.urls")),
    path("financeiro/", include("apps.financeiro.urls")),
    path("leiloes/", include("apps.leiloes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_LOCAL_MEDIA", False) and not getattr(settings, "USE_S3_MEDIA_STORAGE", False):
    urlpatterns += [
        path("media/<path:path>", login_required(serve), {"document_root": settings.MEDIA_ROOT}),
    ]
