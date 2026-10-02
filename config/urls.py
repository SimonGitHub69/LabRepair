"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.templatetags.static import static as static_url
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from config.labrepair_admin import apply_labrepair_admin

apply_labrepair_admin()

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=static_url("securtek/img/favicon.svg"),
            permanent=True,
        ),
    ),
    path("", include("apps.accounts.urls")),
    path("anagrafiche/", include("apps.anagrafiche.urls")),
    path("agenda/", include("apps.agenda.urls")),
    path("pratiche/", include("apps.pratiche.urls")),
    path("", include("apps.core.urls_client")),
    path("", include("apps.dashboard.urls")),
]

# django.conf.urls.static.static() e' no-op se DEBUG=False: in produzione LAN
# serviamo i media esplicitamente quando SERVE_MEDIA=True.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA", False):
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [
        re_path(
            rf"^{media_prefix}(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

handler403 = "apps.core.error_views.permission_denied"

