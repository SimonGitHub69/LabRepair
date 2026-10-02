from django.urls import path

from apps.core.client_update_views import ClientDownloadView, ClientVersionView

app_name = "core_client"

urlpatterns = [
    path("api/client/version/", ClientVersionView.as_view(), name="client_version"),
    path("api/client/download/", ClientDownloadView.as_view(), name="client_download"),
]
