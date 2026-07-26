from django.shortcuts import render


def permission_denied(request, exception=None):
    """Pagina 403 leggibile al posto del generico '403 Forbidden'."""
    return render(
        request,
        "403.html",
        {
            "exception": exception,
        },
        status=403,
    )
