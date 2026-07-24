from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as AuthLoginView
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.forms import LoginForm
from apps.core.negozi import negozio_label, normalize_negozio_code
from apps.core.pc import bind_nome_pc


class LoginView(AuthLoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get("app") == "1":
            request.session["labrepair_app"] = True

        if self.redirect_authenticated_user and request.user.is_authenticated:
            if normalize_negozio_code(request.session.get("negozio")):
                redirect_to = self.get_redirect_url()
                if redirect_to:
                    return redirect(redirect_to)
            # Sessione valida ma negozio assente: mostra login per riselezionarlo.
            return super(AuthLoginView, self).dispatch(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        detected_pc = getattr(form, "detected_nome_pc", "") if form else ""
        pc_config = getattr(form, "detected_pc_config", None) if form else None
        context["detected_nome_pc"] = detected_pc
        context["detected_pc_config"] = pc_config
        if pc_config:
            context["detected_negozio_label"] = negozio_label(pc_config.negozio_default)
        else:
            context["detected_negozio_label"] = ""
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        negozio = normalize_negozio_code(form.cleaned_data.get("negozio"))
        if negozio:
            self.request.session["negozio"] = negozio
        bind_nome_pc(self.request, response, form.cleaned_data.get("nome_pc"))
        return response

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("dashboard:index")


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(View):
    def _logout_and_respond(self, request):
        logout(request)

        silent = request.GET.get("silent") == "1"
        if silent:
            response = HttpResponse(status=204)
            response["Cache-Control"] = "no-store"
            return response

        response = redirect("accounts:login")
        response["Cache-Control"] = "no-store"
        return response

    def post(self, request, *args, **kwargs):
        return self._logout_and_respond(request)

    def get(self, request, *args, **kwargs):
        return self._logout_and_respond(request)
