from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.urls import reverse
from django.views import View

from apps.core.client_update import find_client_package, get_client_update_info


class ClientVersionView(View):
    """Metadati versione client Windows (senza autenticazione)."""

    def get(self, request):
        info = get_client_update_info()
        payload = {
            "version": info["version"],
            "available": info["available"],
            "filename": info["filename"],
            "size": info["size"],
            "download_url": "",
        }
        if info["available"]:
            payload["download_url"] = request.build_absolute_uri(
                reverse("core_client:client_download")
            )
        return JsonResponse(payload)


class ClientDownloadView(View):
    """Download dello zip client Windows corrente."""

    def get(self, request):
        package, _package_version = find_client_package()
        if not package or not package.is_file():
            raise Http404("Pacchetto client non disponibile sul server.")
        return FileResponse(
            package.open("rb"),
            as_attachment=True,
            filename=package.name,
            content_type="application/zip",
        )
