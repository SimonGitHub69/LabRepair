from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.db.models import Q
from django.contrib.messages.views import SuccessMessageMixin

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.anagrafiche.forms import AnagraficaForm, ContattoFormSet, DocumentoIdentitaForm
from apps.anagrafiche.forms.anagrafica import build_indirizzo_formset
from apps.anagrafiche.search import (
    annotate_anagrafica_name_search,
    build_anagrafica_name_search_q,
)
from apps.core.list_pagination import ConfigurablePaginationMixin
from apps.core.negozi import apply_negozio_queryset_filter, normalize_negozio_code
from apps.pratiche.cliente_documento import is_documento_identita_scaduto
from apps.pratiche.cliente_referente import get_referente_from_cliente
from apps.pratiche.models import Pratica


def get_safe_next_url(request):
    next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()
    if not next_url:
        return ""
    if not next_url.startswith("/") or next_url.startswith("//"):
        return ""
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ""
    return next_url


class AnagraficaListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_list.html"
    context_object_name = "anagrafiche"
    paginate_by = 20

    def get_queryset(self):
        queryset = Anagrafica.objects.filter(is_active=True)

        q = (self.request.GET.get("q") or "").strip()
        tipo = (self.request.GET.get("tipo") or "").strip()

        if q:
            queryset = annotate_anagrafica_name_search(queryset).filter(
                build_anagrafica_name_search_q(q, include_contacts=False)
            )

        if tipo:
            queryset = queryset.filter(tipo=tipo)

        return queryset.order_by("cognome", "nome", "ragione_sociale")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipi_anagrafica"] = Anagrafica.Tipo.choices
        context["selected_tipo"] = (self.request.GET.get("tipo") or "").strip()
        query_dict = self.request.GET.copy()
        query_dict.pop("page", None)
        context["filters_query"] = query_dict.urlencode()
        list_path = reverse("anagrafiche:anagrafica_list")
        full_qs = self.request.GET.urlencode()
        context["list_return_url"] = f"{list_path}?{full_qs}" if full_qs else list_path
        return context


class AnagraficaDetailView(LoginRequiredMixin, DetailView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_detail.html"
    context_object_name = "anagrafica"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        anagrafica = self.object
        indirizzi = list(anagrafica.indirizzi.filter(is_active=True))
        context["indirizzo_principale"] = next(
            (ind for ind in indirizzi if ind.principale),
            indirizzi[0] if indirizzi else None,
        )
        if anagrafica.is_cliente:
            initials = f"{(anagrafica.cognome or '')[:1]}{(anagrafica.nome or '')[:1]}"
        else:
            initials = (anagrafica.ragione_sociale or "")[:2]
        context["anagrafica_initials"] = (initials or "?").upper()
        context["documento_scaduto"] = (
            anagrafica.is_cliente and is_documento_identita_scaduto(anagrafica)
        )
        pratiche = apply_negozio_queryset_filter(
            anagrafica.pratiche.filter(is_active=True)
            .exclude(
                stato__in=[
                    Pratica.Stato.COMPLETATA,
                    Pratica.Stato.ANNULLATA,
                    Pratica.Stato.ARCHIVIATA,
                ]
            )
            .select_related("responsabile", "operatore"),
            normalize_negozio_code(self.request.session.get("negozio")),
        )
        context["pratiche_in_essere"] = pratiche
        context["pratiche_in_essere_count"] = pratiche.count()
        context["list_url"] = get_safe_next_url(self.request) or reverse(
            "anagrafiche:anagrafica_list"
        )
        return context


class AnagraficaFormsetMixin:
    contatto_prefix = "contatti"
    indirizzo_prefix = "indirizzi"

    def is_prezioso_context(self):
        return (
            self.request.GET.get("prezioso") == "1"
            or self.request.GET.get("tipologia") == "prezioso"
            or self.request.POST.get("prezioso_mode") == "1"
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prezioso"] = self.is_prezioso_context()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if not getattr(self, "object", None):
            if self.request.GET.get("tipo") == "cliente" or self.is_prezioso_context():
                initial.setdefault("tipo", Anagrafica.Tipo.CLIENTE)
        return initial

    def get_contatto_queryset(self):
        if self.object:
            return self.object.contatti.filter(is_active=True)

        return Contatto.objects.none()

    def get_indirizzo_queryset(self):
        if self.object:
            return self.object.indirizzi.filter(is_active=True)

        return Indirizzo.objects.none()

    def get_contatto_formset(self):
        return ContattoFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix=self.contatto_prefix,
            queryset=self.get_contatto_queryset(),
        )

    def get_indirizzo_formset(self):
        queryset = self.get_indirizzo_queryset()
        # Un form vuoto solo in creazione / senza indirizzi già salvati.
        # Con extra=1 fisso compare un secondo "Indirizzo di residenza" vuoto in modifica.
        has_existing = bool(self.object and self.object.pk and queryset.exists())
        FormSet = build_indirizzo_formset(extra=0 if has_existing else 1)
        formset = FormSet(
            self.request.POST or None,
            instance=self.object,
            prefix=self.indirizzo_prefix,
            queryset=queryset,
        )
        if not self.object:
            for form in formset.forms:
                form.initial.setdefault("tipo", Indirizzo.TipoIndirizzo.RESIDENZA)
                form.initial.setdefault("principale", True)
                form.initial.setdefault("nazione", "Italia")
        return formset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "contatto_formset" not in context:
            context["contatto_formset"] = self.get_contatto_formset()

        if "indirizzo_formset" not in context:
            context["indirizzo_formset"] = self.get_indirizzo_formset()

        context["cliente_prezioso"] = self.is_prezioso_context()
        context["next_url"] = get_safe_next_url(self.request)
        context["documento_scaduto_required"] = (
            self.request.GET.get("documento_scaduto") == "1"
            or self.request.POST.get("documento_scaduto") == "1"
        )
        if (
            context["documento_scaduto_required"]
            and getattr(self, "object", None)
            and is_documento_identita_scaduto(self.object)
        ):
            context["documento_ancora_scaduto"] = True
        else:
            context["documento_ancora_scaduto"] = False
        return context

    def form_valid(self, form):
        contatto_formset = self.get_contatto_formset()
        indirizzo_formset = self.get_indirizzo_formset()

        if not contatto_formset.is_valid() or not indirizzo_formset.is_valid():
            return self.form_invalid_with_formsets(form, contatto_formset, indirizzo_formset)

        if form.cleaned_data.get("tipo") == Anagrafica.Tipo.CLIENTE and self.is_prezioso_context():
            if not self._has_residenza(indirizzo_formset):
                form.add_error(
                    None,
                    "Per oggetti preziosi inserisci almeno un indirizzo di residenza completo.",
                )
                return self.form_invalid_with_formsets(form, contatto_formset, indirizzo_formset)

        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.updated_by = self.request.user
            if not self.object.pk:
                self.object.created_by = self.request.user
            self.object.save()

            self.save_formset(contatto_formset)
            self.save_formset(indirizzo_formset)

        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid_with_formsets(self, form, contatto_formset, indirizzo_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                contatto_formset=contatto_formset,
                indirizzo_formset=indirizzo_formset,
            )
        )

    def save_formset(self, formset):
        formset.instance = self.object
        instances = formset.save(commit=False)

        for instance in instances:
            if hasattr(instance, "valore") and not instance.valore:
                continue

            if hasattr(instance, "indirizzo") and not instance.indirizzo:
                continue

            instance.updated_by = self.request.user
            if not instance.pk:
                instance.created_by = self.request.user
            instance.save()

    @staticmethod
    def _has_residenza(indirizzo_formset):
        for indirizzo_form in indirizzo_formset:
            cleaned_data = getattr(indirizzo_form, "cleaned_data", None) or {}
            if not cleaned_data or cleaned_data.get("DELETE"):
                continue
            indirizzo = (cleaned_data.get("indirizzo") or "").strip()
            comune = (cleaned_data.get("comune") or "").strip()
            cap = (cleaned_data.get("cap") or "").strip()
            provincia = (cleaned_data.get("provincia") or "").strip()
            if indirizzo and comune and cap and provincia:
                return True
        return False


class AnagraficaCreateView(LoginRequiredMixin, AnagraficaFormsetMixin, SuccessMessageMixin, CreateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_message = "Anagrafica creata correttamente."

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})


class AnagraficaUpdateView(LoginRequiredMixin, AnagraficaFormsetMixin, SuccessMessageMixin, UpdateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_message = "Anagrafica aggiornata correttamente."

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url:
            return next_url
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})


class AnagraficaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        anagrafica = get_object_or_404(Anagrafica, pk=kwargs["pk"], is_active=True)
        anagrafica.soft_delete(user=request.user)
        messages.success(request, "Anagrafica eliminata correttamente.")
        return redirect("anagrafiche:anagrafica_list")


class AnagraficaDocumentoUpdateJsonView(LoginRequiredMixin, View):
    """Aggiorna solo i campi documento di un cliente (AJAX dalla scheda pratica)."""

    def post(self, request, pk):
        anagrafica = get_object_or_404(
            Anagrafica,
            pk=pk,
            is_active=True,
            tipo=Anagrafica.Tipo.CLIENTE,
        )
        form = DocumentoIdentitaForm(
            request.POST,
            instance=anagrafica,
            require_valid=True,
        )
        if not form.is_valid():
            first_error = ""
            if form.non_field_errors():
                first_error = str(form.non_field_errors()[0])
            else:
                for field_errors in form.errors.values():
                    if field_errors:
                        first_error = str(field_errors[0])
                        break
            return JsonResponse(
                {
                    "ok": False,
                    "message": first_error or "Controlla i campi del documento.",
                    "errors": form.errors.get_json_data(),
                },
                status=400,
            )

        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save(
            update_fields=[
                "documento_tipo",
                "documento_numero",
                "documento_rilasciato_da",
                "documento_data_rilascio",
                "documento_data_scadenza",
                "stampa_privacy",
                "updated_by",
                "updated_at",
            ]
        )
        referente = get_referente_from_cliente(obj)
        return JsonResponse(
            {
                "ok": True,
                "message": "Documento aggiornato sull'anagrafica.",
                "anagrafica": referente.get("anagrafica"),
            }
        )
