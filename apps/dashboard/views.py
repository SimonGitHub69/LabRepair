from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView
from django.conf import settings
from django.db import connection
from django.utils import timezone
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from apps.anagrafiche.models import Anagrafica
from apps.core.list_pagination import ConfigurablePaginationMixin
from apps.core.models import Azienda, ConfigurazioneMssql
from apps.core.mssql import get_mssql_config
from apps.core.negozi import apply_negozio_queryset_filter, normalize_negozio_code
from apps.dashboard.forms import AziendaForm
from apps.agenda.models import EventoAgenda
from apps.pratiche.models import (
    ComunicazionePratica,
    Operatore,
    Pratica,
    PraticaCategoriaAllegato,
    PraticaCategoria,
    StudioTecnico,
    TipoOggetto,
)

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".doc",
    ".docx",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".xls",
    ".xlsm",
    ".xlsx",
}

NATIVE_OPEN_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".xlsm"}


def file_datetime(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())


def file_type_label(file_name):
    extension = Path(file_name or "").suffix.upper().lstrip(".")
    return extension or "-"


def office_file_priority(file_name):
    return 0 if Path(file_name or "").suffix.lower() in NATIVE_OPEN_EXTENSIONS else 1


def scan_folder_documents(q=""):
    documents = []
    query = q.lower()
    collegamenti = (
        PraticaCategoria.objects.filter(
            is_active=True,
            pratica__is_active=True,
        )
        .exclude(cartella="")
        .select_related("pratica", "categoria", "macro_categoria")
        .prefetch_related("file_metadati")
    )

    for collegamento in collegamenti:
        cartella = (collegamento.cartella or "").strip()

        if not cartella.lower().startswith(("http://", "https://")):
            folder_path = Path(cartella).expanduser()
        else:
            continue

        if not folder_path.exists() or not folder_path.is_dir():
            continue

        metadata_by_path = {
            metadata.percorso_relativo: metadata
            for metadata in collegamento.file_metadati.filter(is_active=True)
        }

        try:
            files = sorted(folder_path.rglob("*"), key=lambda item: str(item.relative_to(folder_path)).lower())
        except OSError:
            continue

        for file_path in files:
            if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
                continue

            relative_name = file_path.relative_to(folder_path).as_posix()
            metadata = metadata_by_path.get(relative_name)
            description = metadata.descrizione if metadata else ""
            pratica = collegamento.pratica
            searchable = " ".join(
                [
                    relative_name,
                    description,
                    pratica.codice,
                    pratica.titolo,
                    collegamento.categoria.denominazione,
                    collegamento.macro_categoria.denominazione if collegamento.macro_categoria else "",
                ]
            ).lower()

            if query and query not in searchable:
                continue

            try:
                stat = file_path.stat()
            except OSError:
                continue

            documents.append(
                {
                    "name": relative_name,
                    "description": description,
                    "type": file_type_label(relative_name),
                    "source": "Cartella categoria",
                    "category": collegamento.categoria.denominazione,
                    "macro": collegamento.macro_categoria.denominazione if collegamento.macro_categoria else "",
                    "pratica": pratica,
                    "updated_at": file_datetime(stat.st_mtime),
                    "open_url": reverse(
                        "pratiche:pratica_categoria_file",
                        kwargs={"pratica_pk": pratica.pk, "pk": collegamento.pk},
                    ) + f"?file={quote(relative_name)}",
                    "open_app_url": (
                        reverse(
                            "pratiche:pratica_categoria_file_open",
                            kwargs={"pratica_pk": pratica.pk, "pk": collegamento.pk},
                        ) + f"?file={quote(relative_name)}&next={quote('/documenti/')}"
                        if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS
                        else ""
                    ),
                    "detail_url": reverse("pratiche:pratica_detail", kwargs={"pk": pratica.pk}),
                    "icon": "ti-folder",
                }
            )

    return documents


def scan_uploaded_category_documents(q=""):
    documents = []
    query = q.lower()
    allegati = (
        PraticaCategoriaAllegato.objects.filter(
            is_active=True,
            pratica_categoria__is_active=True,
            pratica_categoria__pratica__is_active=True,
        )
        .select_related(
            "pratica_categoria__pratica",
            "pratica_categoria__categoria",
            "pratica_categoria__macro_categoria",
        )
        .order_by("file")
    )

    for allegato in allegati:
        pratica_categoria = allegato.pratica_categoria
        pratica = pratica_categoria.pratica
        file_name = allegato.file_nome
        searchable = " ".join(
            [
                file_name,
                allegato.descrizione,
                pratica.codice,
                pratica.titolo,
                pratica_categoria.categoria.denominazione,
                pratica_categoria.macro_categoria.denominazione if pratica_categoria.macro_categoria else "",
            ]
        ).lower()

        if query and query not in searchable:
            continue

        documents.append(
            {
                "name": file_name,
                "description": allegato.descrizione,
                "type": file_type_label(file_name),
                "source": "File singolo",
                "category": pratica_categoria.categoria.denominazione,
                "macro": pratica_categoria.macro_categoria.denominazione if pratica_categoria.macro_categoria else "",
                "pratica": pratica,
                "updated_at": allegato.updated_at,
                "open_url": reverse(
                    "pratiche:pratica_categoria_allegato_file",
                    kwargs={
                        "pratica_pk": pratica.pk,
                        "categoria_pk": pratica_categoria.pk,
                        "pk": allegato.pk,
                    },
                ),
                "open_app_url": (
                    reverse(
                        "pratiche:pratica_categoria_allegato_open",
                        kwargs={
                            "pratica_pk": pratica.pk,
                            "categoria_pk": pratica_categoria.pk,
                            "pk": allegato.pk,
                        },
                    ) + f"?next={quote('/documenti/')}"
                    if Path(file_name).suffix.lower() in NATIVE_OPEN_EXTENSIONS
                    else ""
                ),
                "detail_url": reverse("pratiche:pratica_detail", kwargs={"pk": pratica.pk}),
                "icon": "ti-paperclip",
            }
        )

    return documents


def count_linked_documents():
    categoria_files = len(scan_folder_documents())
    allegati_singoli = PraticaCategoriaAllegato.objects.filter(
        is_active=True,
        pratica_categoria__is_active=True,
        pratica_categoria__pratica__is_active=True,
    ).count()
    comunicazioni = ComunicazionePratica.objects.filter(
        is_active=True,
        allegato__gt="",
        pratica__is_active=True,
    ).count()

    return categoria_files + allegati_singoli + comunicazioni


def count_agenda_items(negozio=""):
    stati_finali = [
        Pratica.Stato.COMPLETATA,
        Pratica.Stato.ANNULLATA,
        Pratica.Stato.ARCHIVIATA,
    ]

    eventi_agenda = (
        EventoAgenda.objects.filter(
            is_active=True,
            pratica__is_active=True,
        )
        .exclude(stato__in=[EventoAgenda.Stato.COMPLETATO, EventoAgenda.Stato.ANNULLATO])
        .exclude(pratica__stato__in=stati_finali)
    )
    if negozio:
        eventi_agenda = eventi_agenda.filter(pratica__negozio=negozio)
    scadenze_pratiche = apply_negozio_queryset_filter(
        Pratica.objects.filter(is_active=True, data_scadenza__isnull=False).exclude(
            stato__in=stati_finali
        ),
        negozio,
    )

    return eventi_agenda.count() + scadenze_pratiche.count()


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        anagrafiche = Anagrafica.objects.filter(is_active=True)
        negozio = normalize_negozio_code(self.request.session.get("negozio"))
        pratiche = apply_negozio_queryset_filter(
            Pratica.objects.filter(is_active=True).exclude(stato=Pratica.Stato.ARCHIVIATA),
            negozio,
        )
        stati_finali = [Pratica.Stato.EVASA, Pratica.Stato.COMPLETATA, Pratica.Stato.ANNULLATA, Pratica.Stato.ARCHIVIATA]
        riparazioni_aperte = pratiche.exclude(stato__in=stati_finali)
        oggi = timezone.localdate()

        context["kpi"] = {
            "anagrafiche": anagrafiche.count(),
            "clienti": anagrafiche.count(),
            "pratiche": riparazioni_aperte.count(),
            "in_laboratorio": pratiche.filter(stato__in=[Pratica.Stato.ACCETTAZIONE, Pratica.Stato.RIPARATORE]).count(),
            "da_consegnare": pratiche.filter(stato=Pratica.Stato.IN_CONSEGNA).count(),
            "scadute": riparazioni_aperte.filter(data_scadenza__lt=oggi).count(),
            "documenti": count_linked_documents(),
            "scadenze": count_agenda_items(negozio),
            "incasso_previsto": riparazioni_aperte.aggregate(total=Sum("prezzo_al"))["total"] or 0,
        }
        context["ultime_anagrafiche"] = anagrafiche.order_by("-created_at")[:5]
        context["ultime_riparazioni"] = (
            pratiche.select_related("cliente", "responsabile", "riparatore", "centro_assistenza")
            .order_by("-data_apertura", "-id")[:8]
        )
        stato_labels = dict(Pratica.Stato.choices)
        stati_riparazioni = [
            {
                "stato": item["stato"],
                "label": stato_labels.get(item["stato"], item["stato"]),
                "totale": item["totale"],
            }
            for item in pratiche.values("stato").annotate(totale=Count("id")).order_by("stato")
        ]
        context["stati_riparazioni"] = stati_riparazioni
        context["totale_stati_riparazioni"] = sum(item["totale"] for item in stati_riparazioni)
        context["riparazioni_in_scadenza"] = (
            riparazioni_aperte.filter(data_scadenza__isnull=False)
            .select_related("cliente")
            .order_by("data_scadenza", "id")[:6]
        )

        return context


class DocumentiView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "dashboard/documenti.html"
    permission_required = "dashboard.access_documenti"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()

        categoria_documents = scan_folder_documents(q)
        allegati_documents = scan_uploaded_category_documents(q)
        comunicazioni = (
            ComunicazionePratica.objects.filter(
                is_active=True,
                allegato__gt="",
                pratica__is_active=True,
            )
            .select_related("pratica")
            .order_by("-data_ora", "-id")
        )

        if q:
            comunicazioni = comunicazioni.filter(
                descrizione__icontains=q
            ) | comunicazioni.filter(
                allegato__icontains=q
            ) | comunicazioni.filter(
                pratica__codice__icontains=q
            ) | comunicazioni.filter(
                pratica__titolo__icontains=q
            )

        documents = []
        documents.extend(categoria_documents)
        documents.extend(allegati_documents)

        for item in comunicazioni[:100]:
            document_name = item.allegato_nome
            documents.append(
                {
                    "name": document_name,
                    "description": item.descrizione,
                    "type": file_type_label(document_name),
                    "source": "Comunicazione",
                    "category": "",
                    "macro": "",
                    "pratica": item.pratica,
                    "updated_at": item.updated_at,
                    "open_url": reverse(
                        "pratiche:comunicazione_preview" if document_name.lower().endswith(".eml") else "pratiche:comunicazione_file",
                        kwargs={"pratica_pk": item.pratica_id, "pk": item.pk},
                    ),
                    "open_app_url": "",
                    "detail_url": reverse("pratiche:pratica_detail", kwargs={"pk": item.pratica_id}),
                    "icon": "ti-mail",
                }
            )

        documents.sort(key=lambda item: (office_file_priority(item["name"]), -item["updated_at"].timestamp(), item["name"].lower()))
        context["documents"] = documents
        context["q"] = q
        context["document_counts"] = {
            "cartelle": len(categoria_documents),
            "singoli": len(allegati_documents),
            "comunicazioni": comunicazioni.count(),
            "totale": len(categoria_documents) + len(allegati_documents) + comunicazioni.count(),
        }

        return context


class SistemaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "dashboard/sistema.html"
    permission_required = "dashboard.access_sistema"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        media_root = str(getattr(settings, "MEDIA_ROOT", ""))

        context["system_status"] = [
            {
                "label": "Ambiente",
                "value": "Sviluppo" if settings.DEBUG else "Produzione",
                "icon": "ti-code",
            },
            {
                "label": "Database",
                "value": connection.vendor.upper(),
                "icon": "ti-database",
            },
            {
                "label": "MS-SQL",
                "value": self._mssql_status_label(),
                "icon": "ti-plug-connected",
            },
            {
                "label": "Media",
                "value": media_root or "Non configurato",
                "icon": "ti-folder-cog",
            },
            {
                "label": "Fuso orario",
                "value": settings.TIME_ZONE,
                "icon": "ti-clock-cog",
            },
        ]
        context["registry_counts"] = [
            {
                "label": "Clienti",
                "value": Anagrafica.objects.filter(is_active=True, tipo=Anagrafica.Tipo.CLIENTE).count(),
            },
            {
                "label": "Fornitori",
                "value": Anagrafica.objects.filter(is_active=True, tipo=Anagrafica.Tipo.FORNITORE).count(),
            },
            {
                "label": "Centro assistenza",
                "value": Anagrafica.objects.filter(
                    is_active=True, tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA
                ).count(),
            },
            {"label": "Tipi oggetto", "value": TipoOggetto.objects.filter(is_active=True).count()},
            {"label": "Riparatori", "value": StudioTecnico.objects.filter(is_active=True).count()},
            {"label": "Operatori", "value": Operatore.objects.filter(is_active=True).count()},
            {"label": "Aziende", "value": Azienda.objects.filter(is_active=True).count()},
        ]
        context["system_links"] = [
            {
                "label": "Aziende",
                "description": "Dati aziendali e logo.",
                "url": reverse("dashboard:azienda_list"),
                "icon": "ti-building-store",
            },
            {
                "label": "Admin Django",
                "description": "Gestione tecnica avanzata dei dati.",
                "url": reverse("admin:index"),
                "icon": "ti-shield-cog",
            },
            {
                "label": "Parametri mail e SQL",
                "description": "SMTP notifiche e collegamento MS-SQL.",
                "url": reverse("agenda:configurazione_email"),
                "icon": "ti-mail-cog",
            },
            {
                "label": "Parametri programma",
                "description": "Interfaccia, barcode e regole operative.",
                "url": reverse("agenda:configurazione_programma"),
                "icon": "ti-adjustments",
            },
            {
                "label": "Parametri PC",
                "description": "Negozio, grafica e stampanti per ogni postazione.",
                "url": reverse("agenda:configurazione_pc_list"),
                "icon": "ti-device-desktop",
            },
            {
                "label": "Comandi vocali",
                "description": "Attiva il microfono e personalizza le frasi riconosciute.",
                "url": reverse("agenda:comandi_voce"),
                "icon": "ti-microphone",
            },
            {
                "label": "Webcam",
                "description": "Test videocamera e acquisizione foto.",
                "url": reverse("dashboard:webcam"),
                "icon": "ti-camera",
            },
        ]

        return context

    @staticmethod
    def _mssql_status_label():
        config = get_mssql_config()
        if not config.attiva:
            return "Disattivato"
        if not config.is_configured:
            return "Da configurare"
        return config.server_display


class WebcamView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/webcam.html"


class AziendaListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = Azienda
    template_name = "dashboard/azienda_list.html"
    context_object_name = "aziende"
    paginate_by = 20

    def get_queryset(self):
        queryset = Azienda.objects.filter(is_active=True)
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(ragione_sociale__icontains=q)
                | Q(partita_iva__icontains=q)
                | Q(codice_fiscale__icontains=q)
                | Q(email__icontains=q)
                | Q(pec__icontains=q)
                | Q(comune__icontains=q)
            )

        return queryset.order_by("ragione_sociale")


class AziendaCreateView(LoginRequiredMixin, CreateView):
    model = Azienda
    form_class = AziendaForm
    template_name = "dashboard/azienda_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Azienda creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:azienda_list")


class AziendaUpdateView(LoginRequiredMixin, UpdateView):
    model = Azienda
    form_class = AziendaForm
    template_name = "dashboard/azienda_form.html"

    def get_queryset(self):
        return Azienda.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Azienda aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:azienda_list")


class AziendaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        azienda = get_object_or_404(Azienda, pk=kwargs["pk"], is_active=True)
        azienda.soft_delete(user=request.user)
        messages.success(request, "Azienda eliminata correttamente.")
        return redirect("dashboard:azienda_list")
