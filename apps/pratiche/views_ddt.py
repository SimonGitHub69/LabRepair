from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from apps.anagrafiche.models import Anagrafica
from apps.core.list_pagination import ConfigurablePaginationMixin
from apps.core.list_sorting import SortableListMixin
from apps.core.negozi import (
    NEGOZI,
    NEGOZIO_FILTER_ALL,
    apply_negozio_queryset_filter,
    negozio_label,
    normalize_negozio_code,
    resolve_negozio_filter,
)
from apps.pratiche.ddt_pdf import (
    build_ddt_pdf_bytes,
    ddt_pdf_filename,
)
from apps.pratiche.ddt_service import (
    add_ddt_riga,
    buste_aperte_queryset,
    buste_per_ddt_edit,
    create_ddt,
    delete_ddt,
    find_busta_aperta_by_codice,
    get_ddt_sezionale_default,
    get_next_ddt_numero,
    remove_ddt_riga,
    serialize_busta_for_ddt,
    snapshot_destinatario_from_centro,
    update_ddt,
)
from apps.pratiche.forms import DdtCreateForm, DdtUpdateForm
from apps.pratiche.models import Ddt, DdtRiga, Pratica


def _get_active_ddt(pk):
    return get_object_or_404(Ddt.objects.filter(is_active=True), pk=pk)


def _session_negozio(request):
    return normalize_negozio_code(request.session.get("negozio"))


def _buste_display_for_create(centro_id, selected_ids=None):
    selected_ids = {int(x) for x in (selected_ids or []) if str(x).isdigit()}
    by_id = {}
    if centro_id and str(centro_id).isdigit():
        for pratica in buste_aperte_queryset(int(centro_id)):
            by_id[pratica.pk] = pratica
    if selected_ids:
        for pratica in (
            Pratica.objects.filter(is_active=True, pk__in=selected_ids)
            .select_related("cliente", "tipo_oggetto", "centro_assistenza")
            .order_by("codice", "id")
        ):
            by_id[pratica.pk] = pratica
    return list(by_id.values())


class DdtListView(LoginRequiredMixin, ConfigurablePaginationMixin, SortableListMixin, ListView):
    model = Ddt
    template_name = "pratiche/ddt_list.html"
    context_object_name = "ddt_list"
    paginate_by = 20
    sort_fields = {
        "numero": ("numero", "sezionale"),
        "data": "data_documento",
        "negozio": "negozio",
        "centro": "centro_assistenza__ragione_sociale",
        "buste": "righe_count",
        "vettore": "vettore",
    }
    default_sort = "data"
    default_dir = "desc"

    def get_negozio_filter(self):
        return resolve_negozio_filter(
            self.request.GET.get("negozio"),
            self.request.session.get("negozio"),
        )

    def get_queryset(self):
        qs = (
            Ddt.objects.filter(is_active=True)
            .select_related("centro_assistenza")
            .annotate(righe_count=Count("righe", filter=Q(righe__is_active=True)))
        )
        qs = apply_negozio_queryset_filter(qs, self.get_negozio_filter())
        q = (self.request.GET.get("q") or "").strip()
        if q:
            filters = (
                Q(sezionale__icontains=q)
                | Q(destinatario_ragione_sociale__icontains=q)
                | Q(centro_assistenza__ragione_sociale__icontains=q)
                | Q(vettore__icontains=q)
            )
            if q.isdigit():
                filters |= Q(numero=int(q))
            elif "/" in q:
                left, _, right = q.partition("/")
                if left.strip().isdigit():
                    filters |= Q(numero=int(left.strip()), sezionale__iexact=(right.strip() or ""))
            qs = qs.filter(filters)
        centro = (self.request.GET.get("centro") or "").strip()
        if centro.isdigit():
            qs = qs.filter(centro_assistenza_id=int(centro))
        return self.apply_list_ordering(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["centro_filter"] = (self.request.GET.get("centro") or "").strip()
        context["centri"] = Anagrafica.objects.filter(
            is_active=True,
            tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA,
        ).order_by("ragione_sociale")
        negozio_filter = self.get_negozio_filter()
        context["negozi"] = NEGOZI
        context["negozio_filter"] = negozio_filter
        context["negozio_filter_all"] = negozio_filter == NEGOZIO_FILTER_ALL
        context["negozio_filter_label"] = negozio_label(negozio_filter)
        negozio_for_next = (
            negozio_filter
            if negozio_filter != NEGOZIO_FILTER_ALL
            else _session_negozio(self.request)
        )
        numero, sezionale = get_next_ddt_numero(negozio=negozio_for_next)
        context["prossimo_numero"] = f"{numero}/{sezionale}"
        return context


class DdtCreateView(LoginRequiredMixin, View):
    template_name = "pratiche/ddt_form.html"

    def _centri_queryset(self):
        return Anagrafica.objects.filter(
            is_active=True,
            tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA,
        ).order_by("ragione_sociale")

    def get(self, request):
        centro_id = (request.GET.get("centro") or "").strip()
        centri = self._centri_queryset()
        pratiche_qs = _buste_display_for_create(centro_id)
        negozio = _session_negozio(request)
        form = DdtCreateForm(
            centri_queryset=centri,
            pratiche_queryset=buste_aperte_queryset(),
            negozio=negozio,
        )
        if centro_id.isdigit():
            form.fields["centro_assistenza"].initial = int(centro_id)

        centro = centri.filter(pk=int(centro_id)).first() if centro_id.isdigit() else None
        snapshot = snapshot_destinatario_from_centro(centro) if centro else {}

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "ddt": None,
                "is_edit": False,
                "centro": centro,
                "snapshot": snapshot,
                "buste": list(pratiche_qs),
                "selected_ids": {b.pk for b in pratiche_qs},
                "numero_previsto": form.numero_previsto,
            },
        )

    def post(self, request):
        centro_id = (request.POST.get("centro_assistenza") or "").strip()
        centri = self._centri_queryset()
        selected_ids = [x for x in request.POST.getlist("pratiche") if str(x).isdigit()]
        pratiche_qs = _buste_display_for_create(centro_id, selected_ids)
        negozio = _session_negozio(request)
        form = DdtCreateForm(
            request.POST,
            centri_queryset=centri,
            pratiche_queryset=buste_aperte_queryset(),
            negozio=negozio,
        )
        centro = centri.filter(pk=int(centro_id)).first() if centro_id.isdigit() else None
        snapshot = snapshot_destinatario_from_centro(centro) if centro else {}

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "ddt": None,
                    "is_edit": False,
                    "centro": centro,
                    "snapshot": snapshot,
                    "buste": pratiche_qs,
                    "selected_ids": {int(x) for x in selected_ids},
                    "numero_previsto": form.numero_previsto,
                },
                status=400,
            )

        try:
            ddt = create_ddt(
                centro_assistenza=form.cleaned_data["centro_assistenza"],
                pratiche=form.cleaned_data["pratiche"],
                user=request.user,
                negozio=negozio,
                sezionale=form.cleaned_data["sezionale"],
                data_documento=form.cleaned_data["data_documento"],
                causale=form.cleaned_data.get("causale"),
                aspetto_beni=form.cleaned_data.get("aspetto_beni"),
                trasporto_a_cura=form.cleaned_data.get("trasporto_a_cura"),
                vettore=form.cleaned_data.get("vettore"),
                peso_lordo_kg=form.cleaned_data.get("peso_lordo_kg"),
                colli=form.cleaned_data.get("colli"),
                data_inizio_trasporto=form.cleaned_data.get("data_inizio_trasporto"),
                note=form.cleaned_data.get("note") or "",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "ddt": None,
                    "is_edit": False,
                    "centro": centro,
                    "snapshot": snapshot,
                    "buste": pratiche_qs,
                    "selected_ids": {int(x) for x in selected_ids},
                    "numero_previsto": form.numero_previsto,
                },
                status=400,
            )

        messages.success(request, f"DDT {ddt.numero_display} creato correttamente.")
        return redirect("pratiche:ddt_update", pk=ddt.pk)


class DdtUpdateView(LoginRequiredMixin, View):
    template_name = "pratiche/ddt_form.html"

    def _context(self, request, ddt, form, buste, status=200):
        righe = list(
            ddt.righe.filter(is_active=True)
            .select_related("pratica", "pratica__cliente")
            .order_by("ordine", "id")
        )
        snapshot = {
            "destinatario_ragione_sociale": ddt.destinatario_ragione_sociale,
            "destinatario_indirizzo": ddt.destinatario_indirizzo,
            "destinatario_cap": ddt.destinatario_cap,
            "destinatario_comune": ddt.destinatario_comune,
            "destinatario_provincia": ddt.destinatario_provincia,
            "destinatario_partita_iva": ddt.destinatario_partita_iva,
            "destinatario_codice_fiscale": ddt.destinatario_codice_fiscale,
            "destinatario_codice_cliente": ddt.destinatario_codice_cliente,
        }
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "ddt": ddt,
                "is_edit": True,
                "centro": ddt.centro_assistenza,
                "snapshot": snapshot,
                "buste": list(buste),
                "righe": righe,
                "selected_ids": {r.pratica_id for r in righe if r.pratica_id},
                "numero_previsto": ddt.numero_display,
            },
            status=status,
        )

    def get(self, request, pk):
        ddt = _get_active_ddt(pk)
        buste = buste_per_ddt_edit(ddt)
        form = DdtUpdateForm(ddt=ddt)
        return self._context(request, ddt, form, buste)

    def post(self, request, pk):
        ddt = _get_active_ddt(pk)
        buste = buste_per_ddt_edit(ddt)
        form = DdtUpdateForm(request.POST, ddt=ddt)
        if not form.is_valid():
            return self._context(request, ddt, form, buste, status=400)

        try:
            update_ddt(
                ddt=ddt,
                user=request.user,
                data_documento=form.cleaned_data["data_documento"],
                causale=form.cleaned_data.get("causale"),
                aspetto_beni=form.cleaned_data.get("aspetto_beni"),
                trasporto_a_cura=form.cleaned_data.get("trasporto_a_cura"),
                vettore=form.cleaned_data.get("vettore"),
                peso_lordo_kg=form.cleaned_data.get("peso_lordo_kg"),
                colli=form.cleaned_data.get("colli"),
                data_inizio_trasporto=form.cleaned_data.get("data_inizio_trasporto"),
                note=form.cleaned_data.get("note") or "",
                refresh_destinatario=bool(form.cleaned_data.get("refresh_destinatario")),
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return self._context(request, ddt, form, buste, status=400)

        messages.success(request, f"DDT {ddt.numero_display} aggiornato correttamente.")
        return redirect("pratiche:ddt_detail", pk=ddt.pk)


class DdtDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ddt = _get_active_ddt(pk)
        numero = ddt.numero_display
        try:
            delete_ddt(ddt=ddt, user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("pratiche:ddt_detail", pk=pk)

        messages.success(request, f"DDT {numero} eliminato correttamente.")
        return redirect("pratiche:ddt_list")


class DdtDetailView(LoginRequiredMixin, DetailView):
    model = Ddt
    template_name = "pratiche/ddt_detail.html"
    context_object_name = "ddt"

    def get_queryset(self):
        return (
            Ddt.objects.filter(is_active=True)
            .select_related("centro_assistenza")
            .prefetch_related(
                Prefetch(
                    "righe",
                    queryset=DdtRiga.objects.filter(is_active=True)
                    .select_related("pratica", "pratica__cliente")
                    .order_by("ordine", "id"),
                )
            )
        )


class DdtRigheView(LoginRequiredMixin, View):
    template_name = "pratiche/ddt_righe_form.html"

    def get(self, request, pk):
        ddt = _get_active_ddt(pk)
        righe = list(
            ddt.righe.filter(is_active=True)
            .select_related("pratica", "pratica__cliente", "pratica__centro_assistenza")
            .order_by("ordine", "id")
        )
        return render(
            request,
            self.template_name,
            {
                "ddt": ddt,
                "righe": righe,
                "buste_disponibili": list(
                    buste_aperte_queryset().select_related("cliente", "centro_assistenza")
                ),
            },
        )


class DdtRigaAddView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ddt = _get_active_ddt(pk)
        pratica_id = (request.POST.get("pratica") or "").strip()
        codice = (request.POST.get("codice") or "").strip()
        pratica = None
        if pratica_id.isdigit():
            pratica = (
                Pratica.objects.filter(is_active=True, pk=int(pratica_id))
                .select_related("cliente", "centro_assistenza")
                .first()
            )
        elif codice:
            pratica = find_busta_aperta_by_codice(codice)
        if not pratica:
            messages.error(
                request,
                "Seleziona una busta o inserisci un numero busta valido (aperta e non già in DDT).",
            )
            return redirect("pratiche:ddt_righe", pk=pk)

        try:
            add_ddt_riga(ddt=ddt, pratica=pratica, user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("pratiche:ddt_righe", pk=pk)

        messages.success(request, f"Aggiunta la busta {pratica.codice} al DDT.")
        return redirect("pratiche:ddt_righe", pk=pk)


class DdtRigaDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, riga_pk):
        ddt = _get_active_ddt(pk)
        riga = get_object_or_404(
            DdtRiga.objects.filter(is_active=True, ddt=ddt).select_related("pratica"),
            pk=riga_pk,
        )
        codice = (riga.pratica.codice if riga.pratica_id else riga.articolo) or "riga"
        try:
            remove_ddt_riga(ddt=ddt, riga=riga, user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("pratiche:ddt_righe", pk=pk)

        messages.success(request, f"Rimossa la busta {codice} dal DDT.")
        return redirect("pratiche:ddt_righe", pk=pk)


class DdtPrintView(LoginRequiredMixin, View):
    def get(self, request, pk):
        ddt = get_object_or_404(
            Ddt.objects.filter(is_active=True).prefetch_related(
                Prefetch(
                    "righe",
                    queryset=DdtRiga.objects.filter(is_active=True)
                    .select_related("pratica")
                    .order_by("ordine", "id"),
                )
            ),
            pk=pk,
        )
        try:
            pdf_bytes = build_ddt_pdf_bytes(ddt)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("pratiche:ddt_detail", pk=pk)

        filename = ddt_pdf_filename(ddt)
        fmt = (request.GET.get("format") or "").lower()
        if fmt == "pdf":
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            response["X-Frame-Options"] = "SAMEORIGIN"
            return response

        referer = request.META.get("HTTP_REFERER") or ""
        if "/pratiche/ddt/" in referer and referer.rstrip("/").endswith(str(pk)):
            return_url = reverse("pratiche:ddt_detail", args=[ddt.pk])
        else:
            return_url = reverse("pratiche:ddt_list")

        import base64

        return render(
            request,
            "pratiche/ddt_print.html",
            {
                "ddt": ddt,
                "document_title": f"DDT {ddt.numero_display}",
                "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
                "return_url": return_url,
            },
        )


class DdtBusteJsonView(LoginRequiredMixin, View):
    """Elenco buste aperte per centro, oppure lookup singolo per codice."""

    def get(self, request):
        centro_id = (request.GET.get("centro") or "").strip()
        sezionale_param = (request.GET.get("sezionale") or "").strip() or None
        codice = (request.GET.get("codice") or "").strip()
        negozio = _session_negozio(request)

        if codice:
            pratica = find_busta_aperta_by_codice(codice)
            if not pratica:
                return JsonResponse(
                    {
                        "ok": False,
                        "error": f"Busta {codice.upper()} non trovata, chiusa o già in un DDT.",
                    },
                    status=404,
                )
            return JsonResponse(
                {
                    "ok": True,
                    "busta": serialize_busta_for_ddt(pratica, extra=True),
                }
            )

        if not centro_id.isdigit():
            numero, sezionale = get_next_ddt_numero(sezionale_param, negozio=negozio)
            return JsonResponse(
                {
                    "ok": True,
                    "buste": [],
                    "destinatario": {},
                    "sezionale": sezionale,
                    "prossimo_numero": f"{numero}/{sezionale}",
                }
            )

        centro = get_object_or_404(
            Anagrafica,
            pk=int(centro_id),
            is_active=True,
            tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA,
        )
        buste = [serialize_busta_for_ddt(p) for p in buste_aperte_queryset(centro.pk)]
        numero, sezionale = get_next_ddt_numero(sezionale_param, negozio=negozio)
        return JsonResponse(
            {
                "ok": True,
                "buste": buste,
                "destinatario": snapshot_destinatario_from_centro(centro),
                "sezionale": sezionale,
                "prossimo_numero": f"{numero}/{sezionale}",
            }
        )
