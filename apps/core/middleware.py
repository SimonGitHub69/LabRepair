from django.shortcuts import redirect

from apps.core.negozi import normalize_negozio_code
from apps.core.pc import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    SESSION_KEY,
    is_valid_pc_name,
    normalize_nome_pc,
)


class RequireNegozioMiddleware:
    EXEMPT_PREFIXES = (
        "/login/",
        "/logout/",
        "/admin/",
        "/static/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            if not any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
                if not normalize_negozio_code(request.session.get("negozio")):
                    return redirect("accounts:login")
        return self.get_response(request)


class BindClientPcMiddleware:
    """
    Il browser non puo' leggere COMPUTERNAME.
    Il launcher LabRepairApp apre /login/?pc=%COMPUTERNAME% e qui lo salviamo
    in sessione + cookie, cosi' Parametri PC e login riconoscono la postazione.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from_query = normalize_nome_pc(
            request.GET.get("pc") or request.GET.get("nome_pc") or ""
        )
        set_cookie_name = ""
        clear_cookie = False

        if is_valid_pc_name(from_query):
            request.session[SESSION_KEY] = from_query
            set_cookie_name = from_query
        else:
            cookie_val = normalize_nome_pc(request.COOKIES.get(COOKIE_NAME))
            session_val = normalize_nome_pc(request.session.get(SESSION_KEY))
            if cookie_val and not is_valid_pc_name(cookie_val):
                clear_cookie = True
            if session_val and not is_valid_pc_name(session_val):
                request.session.pop(SESSION_KEY, None)

        response = self.get_response(request)

        if set_cookie_name:
            response.set_cookie(
                COOKIE_NAME,
                set_cookie_name,
                max_age=COOKIE_MAX_AGE,
                samesite="Lax",
                httponly=False,
            )
        elif clear_cookie:
            response.delete_cookie(COOKIE_NAME)

        return response
