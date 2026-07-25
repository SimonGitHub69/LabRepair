import calendar
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View

from apps.agenda.forms import ConfigurazioneNotificaEmailForm, EventoAgendaForm
from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda
from apps.core.forms import (
    ComandiVoceForm,
    ConfigurazioneMssqlForm,
    ConfigurazionePCForm,
    ConfigurazioneProgrammaForm,
)
from apps.core.list_pagination import ConfigurablePaginationMixin
from apps.core.mail import parse_email_destinatari, send_smtp_email
from apps.core.models import ConfigurazioneMssql, ConfigurazionePC, ConfigurazioneProgramma
from apps.core.mssql import config_from_post, test_mssql_connection
from apps.core.pc import detect_client_pc_name
from apps.core.programma import get_mailto_preview
from apps.core.negozi import (
    NEGOZI,
    NEGOZIO_FILTER_ALL,
    apply_negozio_queryset_filter,
    negozio_label,
    resolve_negozio_filter,
)
from apps.pratiche.models import Pratica


def get_pratica_corrente(pratica_id):
    if not pratica_id:
        return None
    return (
        Pratica.objects.filter(is_active=True, pk=pratica_id)
        .select_related("cliente")
        .first()
    )


def get_agenda_filters(request):
    pratica_id = (request.GET.get("pratica") or "").strip()
    stato = (request.GET.get("stato") or "").strip()
    negozio_filter = resolve_negozio_filter(
        request.GET.get("negozio"),
        request.session.get("negozio"),
    )
    return pratica_id, stato, negozio_filter


def build_agenda_filter_query(pratica_id="", stato="", negozio_filter=""):
    from urllib.parse import urlencode

    params = {}
    if pratica_id:
        params["pratica"] = pratica_id
    if stato:
        params["stato"] = stato
    if negozio_filter:
        params["negozio"] = negozio_filter
    return urlencode(params)


def get_agenda_pratiche_queryset(stato="", negozio_filter=""):
    queryset = Pratica.objects.filter(is_active=True).order_by("-data_apertura", "-id")
    if stato:
        queryset = queryset.filter(stato=stato)
    return apply_negozio_queryset_filter(queryset, negozio_filter)


def apply_agenda_event_filters(queryset, pratica_id="", stato="", negozio_filter=""):
    if pratica_id:
        queryset = queryset.filter(pratica_id=pratica_id)
    if stato:
        queryset = queryset.filter(pratica__stato=stato)
    return apply_negozio_queryset_filter(queryset, negozio_filter, field="pratica__negozio")


def agenda_filter_context(pratica_id, stato, negozio_filter):
    return {
        "pratiche": get_agenda_pratiche_queryset(stato, negozio_filter),
        "stati": [
            (stato.value, stato.label) for stato in Pratica.STATI_SELEZIONABILI
        ],
        "negozi": NEGOZI,
        "selected_pratica": pratica_id,
        "selected_stato": stato,
        "negozio_filter": negozio_filter,
        "negozio_filter_all": negozio_filter == NEGOZIO_FILTER_ALL,
        "negozio_filter_label": negozio_label(negozio_filter),
        "filter_query": build_agenda_filter_query(pratica_id, stato, negozio_filter),
        "pratica_corrente": get_pratica_corrente(pratica_id),
    }

class PraticaScadenzaAgendaItem:
    tipo = EventoAgenda.Tipo.SCADENZA
    stato = EventoAgenda.Stato.PROGRAMMATO
    ora_inizio = None
    ora_fine = None
    data_fine = None
    descrizione = "Data prevista consegna indicata nella riparazione."
    is_pratica_scadenza = True

    def __init__(self, pratica):
        self.pk = None
        self.pratica = pratica
        self.titolo = f"Scadenza {pratica.codice}"
        self.data_inizio = pratica.data_scadenza
        self.data_termine = pratica.data_scadenza

    def get_tipo_display(self):
        return "Scadenza riparazione"

    def get_stato_display(self):
        return "Programmato"


def get_pratica_deadline_items(start_date, end_date, pratica_id="", stato="", negozio_filter=""):
    stati_finali = [
        Pratica.Stato.COMPLETATA,
        Pratica.Stato.ANNULLATA,
        Pratica.Stato.ARCHIVIATA,
    ]
    pratiche = (
        Pratica.objects.filter(
            is_active=True,
            data_scadenza__gte=start_date,
            data_scadenza__lte=end_date,
        )
        .exclude(stato__in=stati_finali)
        .select_related("cliente")
        .order_by("data_scadenza", "codice")
    )

    if pratica_id:
        pratiche = pratiche.filter(pk=pratica_id)
    if stato:
        pratiche = pratiche.filter(stato=stato)
    pratiche = apply_negozio_queryset_filter(pratiche, negozio_filter)

    return [PraticaScadenzaAgendaItem(pratica) for pratica in pratiche]


class AgendaCalendarView(LoginRequiredMixin, TemplateView):
    template_name = "agenda/agenda_calendar.html"

    def get_month_date(self):
        today = timezone.localdate()
        year = self.request.GET.get("year")
        month = self.request.GET.get("month")

        try:
            year = int(year or today.year)
            month = int(month or today.month)
            return date(year, month, 1)
        except ValueError:
            return date(today.year, today.month, 1)

    def get_events_queryset(self, month_start, month_end, pratica_id="", stato="", negozio_filter=""):
        queryset = (
            EventoAgenda.objects.filter(is_active=True)
            .filter(data_inizio__lte=month_end)
            .filter(Q(data_fine__isnull=True, data_inizio__gte=month_start) | Q(data_fine__gte=month_start))
            .select_related("pratica", "pratica__cliente")
        )
        return apply_agenda_event_filters(queryset, pratica_id, stato, negozio_filter).order_by(
            "data_inizio", "ora_inizio", "titolo"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month_start = self.get_month_date()
        _, days_in_month = calendar.monthrange(month_start.year, month_start.month)
        month_end = date(month_start.year, month_start.month, days_in_month)
        previous_month = date(month_start.year - 1, 12, 1) if month_start.month == 1 else date(month_start.year, month_start.month - 1, 1)
        next_month = date(month_start.year + 1, 1, 1) if month_start.month == 12 else date(month_start.year, month_start.month + 1, 1)
        pratica_id, stato, negozio_filter = get_agenda_filters(self.request)
        events = list(self.get_events_queryset(month_start, month_end, pratica_id, stato, negozio_filter))
        events.extend(get_pratica_deadline_items(month_start, month_end, pratica_id, stato, negozio_filter))
        events.sort(key=lambda event: (event.data_inizio, event.ora_inizio or time.min, event.tipo, event.titolo))
        events_by_day = {}

        for event in events:
            current = max(event.data_inizio, month_start)
            end = min(event.data_termine, month_end)

            while current <= end:
                events_by_day.setdefault(current, []).append(event)
                current = date.fromordinal(current.toordinal() + 1)

        weeks = []
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month):
            weeks.append(
                [
                    {
                        "date": day,
                        "in_month": day.month == month_start.month,
                        "is_today": day == timezone.localdate(),
                        "events": events_by_day.get(day, []),
                    }
                    for day in week
                ]
            )

        today = timezone.localdate()
        context.update(
            {
                "month_start": month_start,
                "previous_month": previous_month,
                "next_month": next_month,
                "weeks": weeks,
                "events": events,
                "upcoming_events": [
                    event
                    for event in events
                    if event.data_termine >= today
                    and event.stato not in {EventoAgenda.Stato.COMPLETATO, EventoAgenda.Stato.ANNULLATO}
                ][:12],
            }
        )
        context.update(agenda_filter_context(pratica_id, stato, negozio_filter))
        return context


class AgendaDayView(LoginRequiredMixin, TemplateView):
    template_name = "agenda/agenda_day.html"

    def get_selected_date(self):
        selected_date = self.request.GET.get("data") or ""

        try:
            return date.fromisoformat(selected_date)
        except ValueError:
            return timezone.localdate()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_date = self.get_selected_date()
        pratica_id, stato, negozio_filter = get_agenda_filters(self.request)
        events = list(
            apply_agenda_event_filters(
                EventoAgenda.objects.filter(is_active=True)
                .filter(data_inizio__lte=selected_date)
                .filter(Q(data_fine__isnull=True, data_inizio=selected_date) | Q(data_fine__gte=selected_date))
                .select_related("pratica", "pratica__cliente"),
                pratica_id,
                stato,
                negozio_filter,
            ).order_by("ora_inizio", "tipo", "titolo")
        )

        events.extend(get_pratica_deadline_items(selected_date, selected_date, pratica_id, stato, negozio_filter))
        events.sort(key=lambda event: (event.ora_inizio or time.min, event.tipo, event.titolo))

        previous_day = selected_date - timedelta(days=1)
        next_day = selected_date + timedelta(days=1)
        context.update(
            {
                "selected_date": selected_date,
                "previous_day": previous_day,
                "next_day": next_day,
                "events": events,
            }
        )
        context.update(agenda_filter_context(pratica_id, stato, negozio_filter))
        return context


class EventoAgendaCreateView(LoginRequiredMixin, CreateView):
    model = EventoAgenda
    form_class = EventoAgendaForm
    template_name = "agenda/evento_form.html"

    def get_initial(self):
        initial = super().get_initial()
        pratica_id = self.request.GET.get("pratica") or ""
        data = self.request.GET.get("data") or ""

        if pratica_id:
            initial["pratica"] = pratica_id

        if data:
            try:
                initial["data_ora"] = datetime.combine(date.fromisoformat(data), time(9, 0))
            except ValueError:
                pass

        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Evento agenda creato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nuovo evento"
        context["cancel_url"] = self.get_success_url()
        pratica_id = self.request.GET.get("pratica") or self.request.POST.get("pratica") or ""
        context["pratica_corrente"] = get_pratica_corrente(pratica_id)
        return context

    def get_success_url(self):
        pratica_id = self.request.GET.get("pratica") or self.request.POST.get("pratica") or ""
        url = reverse("agenda:calendar")

        if pratica_id:
            return f"{url}?pratica={pratica_id}"

        return url


class EventoAgendaUpdateView(LoginRequiredMixin, UpdateView):
    model = EventoAgenda
    form_class = EventoAgendaForm
    template_name = "agenda/evento_form.html"

    def get_queryset(self):
        return EventoAgenda.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Evento agenda aggiornato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifica evento"
        context["cancel_url"] = self.get_success_url()
        context["pratica_corrente"] = self.object.pratica if self.object else None
        return context

    def get_success_url(self):
        return f"{reverse('agenda:calendar')}?pratica={self.object.pratica_id}"


class EventoAgendaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        evento = get_object_or_404(EventoAgenda, pk=kwargs["pk"], is_active=True)
        pratica_id = evento.pratica_id
        evento.soft_delete(user=request.user)
        messages.success(request, "Evento agenda eliminato correttamente.")
        return redirect(f"{reverse('agenda:calendar')}?pratica={pratica_id}")


class ParametriSistemaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = "agenda/configurazione_email_form.html"
    permission_required = "agenda.access_parametri_mail_sql"
    raise_exception = True

    def get_context(self, email_form=None, mssql_form=None):
        return {
            "email_form": email_form or ConfigurazioneNotificaEmailForm(
                instance=ConfigurazioneNotificaEmail.get_solo()
            ),
            "mssql_form": mssql_form or ConfigurazioneMssqlForm(
                instance=ConfigurazioneMssql.get_solo()
            ),
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        action = (request.POST.get("action") or "mail").strip()

        if action == "test_mssql":
            instance = ConfigurazioneMssql.get_solo()
            config = config_from_post(request.POST, instance)
            result = test_mssql_connection(config)
            form = ConfigurazioneMssqlForm(request.POST, instance=instance)

            if result.ok:
                messages.success(request, result.message)
            else:
                messages.error(request, result.message)

            return render(
                request,
                self.template_name,
                self.get_context(mssql_form=form),
            )

        if action == "mssql":
            instance = ConfigurazioneMssql.get_solo()
            form = ConfigurazioneMssqlForm(request.POST, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.updated_by = request.user
                if not obj.created_by:
                    obj.created_by = request.user
                obj.save()
                messages.success(request, "Parametri MS-SQL salvati correttamente.")
                return redirect("agenda:configurazione_email")
            return render(
                request,
                self.template_name,
                self.get_context(mssql_form=form),
            )

        instance = ConfigurazioneNotificaEmail.get_solo()
        form = ConfigurazioneNotificaEmailForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            if not obj.created_by:
                obj.created_by = request.user
            obj.save()
            messages.success(request, "Parametri mail salvati correttamente.")
            return redirect("agenda:configurazione_email")
        return render(
            request,
            self.template_name,
            self.get_context(email_form=form),
        )


class ParametriProgrammaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = "agenda/configurazione_programma_form.html"
    permission_required = "core.access_parametri_programma"
    raise_exception = True

    def get_context(self, form=None, mailto_destinatario=""):
        instance = ConfigurazioneProgramma.get_solo()
        form = form or ConfigurazioneProgrammaForm(instance=instance)
        oggetto = (form["mailto_oggetto"].value() if form.is_bound else instance.mailto_oggetto) or ""
        corpo = (form["mailto_corpo"].value() if form.is_bound else instance.mailto_corpo) or ""
        smtp = ConfigurazioneNotificaEmail.get_solo()
        default_dest = ""
        if mailto_destinatario:
            default_dest = mailto_destinatario
        elif getattr(self.request.user, "email", ""):
            default_dest = self.request.user.email
        else:
            destinatari = parse_email_destinatari(smtp.destinatari_default)
            default_dest = destinatari[0] if destinatari else (smtp.mittente or "")

        return {
            "form": form,
            "mailto_preview": get_mailto_preview(
                oggetto_template=oggetto or None,
                corpo_template=corpo,
            ),
            "smtp_attivo": bool(smtp.attiva and smtp.host and smtp.mittente),
            "mailto_destinatario": default_dest,
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        action = (request.POST.get("action") or "save").strip()
        instance = ConfigurazioneProgramma.get_solo()

        if action == "test_mailto":
            form = ConfigurazioneProgrammaForm(request.POST, instance=instance)
            destinatario = (request.POST.get("mailto_destinatario") or "").strip()
            # Anteprima/test usano i valori del form anche se non ancora salvati.
            oggetto_tpl = (request.POST.get("mailto_oggetto") or "").strip()
            corpo_tpl = (request.POST.get("mailto_corpo") or "").strip()
            preview = get_mailto_preview(
                oggetto_template=oggetto_tpl or None,
                corpo_template=corpo_tpl,
            )
            result = send_smtp_email(
                config=ConfigurazioneNotificaEmail.get_solo(),
                destinatari=parse_email_destinatari(destinatario),
                subject=preview["oggetto"],
                body=preview["corpo"]
                or (
                    "Mail di prova da LabRepair.\n\n"
                    "Questa è una verifica dell'oggetto e del testo configurati "
                    "per le mail da elenco riparazioni."
                ),
            )
            if result.ok:
                messages.success(request, result.message)
            else:
                messages.error(request, result.message)
            return render(
                request,
                self.template_name,
                self.get_context(form=form, mailto_destinatario=destinatario),
            )

        form = ConfigurazioneProgrammaForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            if not obj.created_by:
                obj.created_by = request.user
            obj.save()
            messages.success(request, "Parametri programma salvati correttamente.")
            return redirect("agenda:configurazione_programma")
        return render(request, self.template_name, self.get_context(form=form))


class ParametriComandiVoceView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = "agenda/comandi_voce_form.html"
    permission_required = "core.access_parametri_programma"
    raise_exception = True

    def get_context(self, form=None):
        instance = ConfigurazioneProgramma.get_solo()
        return {
            "form": form or ComandiVoceForm(instance=instance),
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        instance = ConfigurazioneProgramma.get_solo()
        form = ComandiVoceForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            if not obj.created_by:
                obj.created_by = request.user
            obj.save()
            messages.success(request, "Comandi vocali salvati correttamente.")
            return redirect("agenda:comandi_voce")
        return render(request, self.template_name, self.get_context(form=form))


class ConfigurazionePCListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = ConfigurazionePC
    template_name = "agenda/configurazione_pc_list.html"
    context_object_name = "postazioni"
    paginate_by = 20

    def get_queryset(self):
        queryset = ConfigurazionePC.objects.filter(is_active=True)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            queryset = queryset.filter(
                Q(nome_pc__icontains=q)
                | Q(descrizione__icontains=q)
                | Q(note__icontains=q)
            )
        return queryset.order_by("nome_pc")


class ConfigurazionePCCreateView(LoginRequiredMixin, CreateView):
    model = ConfigurazionePC
    form_class = ConfigurazionePCForm
    template_name = "agenda/configurazione_pc_form.html"

    def get_detected_nome_pc(self):
        return detect_client_pc_name(self.request)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        detected = self.get_detected_nome_pc()
        # Readonly solo se il nome rilevato e' plausibile (non IP/frammenti).
        kwargs["nome_pc_readonly"] = bool(detected)
        kwargs["forced_nome_pc"] = detected
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        nome_pc = self.get_detected_nome_pc()
        if nome_pc:
            initial["nome_pc"] = nome_pc
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        detected = self.get_detected_nome_pc()
        context["nome_pc_rilevato"] = detected
        context["nome_pc_auto"] = True
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Postazione PC creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("agenda:configurazione_pc_list")


class ConfigurazionePCUpdateView(LoginRequiredMixin, UpdateView):
    model = ConfigurazionePC
    form_class = ConfigurazionePCForm
    template_name = "agenda/configurazione_pc_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["nome_pc_readonly"] = True
        return kwargs

    def get_queryset(self):
        return ConfigurazionePC.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Postazione PC aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("agenda:configurazione_pc_list")


class ConfigurazionePCDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        postazione = get_object_or_404(ConfigurazionePC, pk=kwargs["pk"], is_active=True)
        postazione.soft_delete(user=request.user)
        messages.success(request, "Postazione PC eliminata correttamente.")
        return redirect("agenda:configurazione_pc_list")
