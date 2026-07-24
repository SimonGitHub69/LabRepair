import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.anagrafiche.cie import CieReadError, read_cie


class AnagraficaCieReadView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse(
                {"ok": False, "message": "Richiesta non valida."},
                status=400,
            )

        can = (payload.get("can") or "").strip()
        try:
            data = read_cie(can)
        except CieReadError as exc:
            return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        except Exception:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "Errore imprevisto durante la lettura della CIE.",
                },
                status=500,
            )

        return JsonResponse({"ok": True, "data": data})
