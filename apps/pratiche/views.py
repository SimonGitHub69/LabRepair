from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files import File
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View
from datetime import datetime
from email import policy
from email.parser import BytesParser
import os
from pathlib import Path
import subprocess
from urllib.parse import quote, unquote, urlparse
from urllib.parse import urlencode

from apps.core.list_pagination import ConfigurablePaginationMixin
from apps.core.negozi import (
    NEGOZI,
    NEGOZIO_FILTER_ALL,
    apply_negozio_queryset_filter,
    negozio_label,
    normalize_negozio_code,
    resolve_negozio_filter,
)
from apps.core.programma import (
    build_mailto_href,
    format_mailto_corpo,
    format_mailto_oggetto,
    get_comunicazioni_formato_data,
    get_mailto_corpo_template,
    get_mailto_oggetto_template,
    layout_compatto,
    operatore_primo_nuova_riparazione,
)
from apps.pratiche.cliente_documento import (
    documento_scaduto_message,
    documento_scaduto_privacy_message,
    is_documento_identita_scaduto,
)
from apps.pratiche.cliente_referente import (
    cliente_referente_url_template,
    get_referente_from_cliente,
    get_referente_from_cliente_id,
)
from apps.pratiche.foto import delete_pratica_foto_ids, save_pratica_foto_uploads
from apps.pratiche.gs_articoli import sync_pratica_to_gs_articoli
from apps.pratiche.codice import get_next_pratica_codice, reserve_pratica_codice


def decode_email_header(message, header_name):
    value = message.get(header_name, "")
    return str(value) if value else ""


def extract_eml_preview(file_obj):
    message = BytesParser(policy=policy.default).parse(file_obj)
    plain_body = ""
    html_body = ""
    attachments = []

    for part in message.walk():
        if part.is_multipart():
            continue

        disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        filename = part.get_filename()

        if disposition == "attachment" or filename:
            attachments.append(
                {
                    "name": filename or "Allegato senza nome",
                    "content_type": content_type,
                }
            )
            continue

        if content_type == "text/plain" and not plain_body:
            plain_body = part.get_content()

        if content_type == "text/html" and not html_body:
            html_body = part.get_content()

    if not plain_body and not html_body and not message.is_multipart():
        payload = message.get_content()
        if isinstance(payload, str):
            plain_body = payload

    return {
        "subject": decode_email_header(message, "subject"),
        "from": decode_email_header(message, "from"),
        "to": decode_email_header(message, "to"),
        "cc": decode_email_header(message, "cc"),
        "date": decode_email_header(message, "date"),
        "plain_body": plain_body,
        "html_body": html_body,
        "attachments": attachments,
    }

from apps.pratiche.forms import (
    CategoriaPraticaForm,
    ComunicazionePraticaForm,
    MacroCategoriaPraticaForm,
    OperatoreForm,
    PraticaForm,
    PraticaCategoriaAllegatoUploadForm,
    PraticaCategoriaForm,
    PraticaCategoriaFileUploadForm,
    PraticaCategoriaFormSet,
    PraticaMacroCategoriaApplyForm,
    StudioTecnicoForm,
    TipoOggettoForm,
)
from apps.agenda.models import EventoAgenda
from apps.anagrafiche.models import Anagrafica
from apps.pratiche.models import (
    CategoriaPratica,
    ComunicazionePratica,
    MacroCategoriaPratica,
    Operatore,
    Pratica,
    PraticaCategoriaAllegato,
    PraticaCategoria,
    PraticaCategoriaFile,
    PraticaFoto,
    PraticaMacroCategoria,
    StudioTecnico,
    TipoOggetto,
)


SUPPORTED_FOLDER_EXTENSIONS = {
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


def office_file_priority(file_path):
    return 0 if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS else 1


def open_with_default_application(file_path):
    if os.name == "nt":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(file_path)], shell=False)
            return
        except OSError:
            pass

    os.startfile(str(file_path))


def is_external_link(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def format_file_datetime(timestamp):
    value = datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())
    return value.strftime("%d/%m/%Y %H:%M")


def get_pratica_categoria_or_404(pratica_pk, pk):
    return get_object_or_404(
        PraticaCategoria,
        pk=pk,
        pratica_id=pratica_pk,
        is_active=True,
    )


def get_pratica_categoria_folder_path(pratica_categoria):
    folder_value = (pratica_categoria.cartella or "").strip()

    if not folder_value or is_external_link(folder_value):
        return None

    folder_path = Path(folder_value).expanduser().resolve()

    if not folder_path.exists() or not folder_path.is_dir():
        return None

    return folder_path


def resolve_categoria_file_path(pratica_categoria, relative_file):
    folder_path = get_pratica_categoria_folder_path(pratica_categoria)
    file_name = unquote(relative_file or "").strip()

    if not folder_path or not file_name:
        raise Http404("File non disponibile")

    file_path = (folder_path / file_name).resolve()

    if folder_path not in file_path.parents:
        raise Http404("Percorso non valido")

    if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
        raise Http404("File non disponibile")

    return folder_path, file_path


def resolve_preview_folder_file_path(folder_value, relative_file):
    folder_text = (folder_value or "").strip()
    file_name = unquote(relative_file or "").strip()

    if not folder_text or not file_name or is_external_link(folder_text):
        raise Http404("File non disponibile")

    folder_path = Path(folder_text).expanduser().resolve()

    if not folder_path.exists() or not folder_path.is_dir():
        raise Http404("Cartella non disponibile")

    file_path = (folder_path / file_name).resolve()

    if folder_path not in file_path.parents:
        raise Http404("Percorso non valido")

    if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
        raise Http404("File non disponibile")

    return folder_path, file_path


def get_pratica_categoria_allegato_or_404(pratica_pk, categoria_pk, pk):
    return get_object_or_404(
        PraticaCategoriaAllegato,
        pk=pk,
        pratica_categoria_id=categoria_pk,
        pratica_categoria__pratica_id=pratica_pk,
        is_active=True,
    )


def build_uploaded_file_entry(allegato):
    file_path = Path(allegato.file.path)

    try:
        stat = file_path.stat()
        size_kb = max(1, round(stat.st_size / 1024))
        modified_at = format_file_datetime(stat.st_mtime)
    except OSError:
        size_kb = "-"
        modified_at = "-"

    return {
        "id": allegato.pk,
        "name": allegato.file_nome,
        "description": allegato.descrizione,
        "extension": file_path.suffix.upper().lstrip(".") or "-",
        "size_kb": size_kb,
        "modified_at": modified_at,
        "open_url": reverse(
            "pratiche:pratica_categoria_allegato_file",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        ),
        "open_app_url": reverse(
            "pratiche:pratica_categoria_allegato_open",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        )
        if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS
        else "",
        "delete_url": reverse(
            "pratiche:pratica_categoria_allegato_delete",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        ),
        "destroy_url": reverse(
            "pratiche:pratica_categoria_allegato_destroy",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        ),
    }


def create_category_attachment_from_path(pratica_categoria, selected_path, user=None):
    file_path = Path(selected_path).expanduser().resolve()

    if not file_path.exists() or not file_path.is_file():
        raise ValueError("File non trovato")

    if file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
        raise ValueError("Tipo file non supportato")

    allegato = PraticaCategoriaAllegato(
        pratica_categoria=pratica_categoria,
        descrizione=file_path.name,
        created_by=user,
        updated_by=user,
    )

    with file_path.open("rb") as source:
        allegato.file.save(file_path.name, File(source), save=False)

    allegato.save()
    return allegato


def get_supported_file_entries(folder_path, pratica_categoria=None):
    entries = []
    metadata_by_path = {}

    if pratica_categoria:
        metadata_by_path = {
            metadata.percorso_relativo: metadata
            for metadata in pratica_categoria.file_metadati.filter(is_active=True)
        }

    for file_path in sorted(
        folder_path.rglob("*"),
        key=lambda item: (office_file_priority(item), str(item.relative_to(folder_path)).lower()),
    ):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
            continue

        stat = file_path.stat()
        relative_path = file_path.relative_to(folder_path)
        relative_path_text = relative_path.as_posix()
        metadata = metadata_by_path.get(relative_path_text)

        if metadata and metadata.scollegato:
            continue

        url = ""
        open_app_url = ""
        preview_open_url = ""
        description_url = ""
        delete_url = ""
        unlink_url = ""

        if pratica_categoria:
            url = reverse(
                "pratiche:pratica_categoria_file",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            ) + f"?file={quote(relative_path_text)}"
            if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS:
                open_app_url = reverse(
                    "pratiche:pratica_categoria_file_open",
                    kwargs={
                        "pratica_pk": pratica_categoria.pratica_id,
                        "pk": pratica_categoria.pk,
                    },
                ) + f"?file={quote(relative_path_text)}"
            description_url = reverse(
                "pratiche:pratica_categoria_file_description",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            )
            delete_url = reverse(
                "pratiche:pratica_categoria_file_delete",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            )
            unlink_url = reverse(
                "pratiche:pratica_categoria_file_unlink",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            )
        else:
            preview_open_url = reverse("pratiche:folder_preview_file_open") + (
                f"?path={quote(str(folder_path))}&file={quote(relative_path_text)}"
            )
            delete_url = reverse("pratiche:folder_preview_file_delete")

        entries.append(
            {
                "name": relative_path_text,
                "description": metadata.descrizione if metadata else "",
                "extension": file_path.suffix.upper().lstrip("."),
                "size_kb": max(1, round(stat.st_size / 1024)),
                "created_at": format_file_datetime(stat.st_ctime),
                "modified_at": format_file_datetime(stat.st_mtime),
                "url": url,
                "open_app_url": open_app_url,
                "preview_open_url": preview_open_url,
                "description_url": description_url,
                "delete_url": delete_url,
                "unlink_url": unlink_url,
            }
        )

    return entries


def build_folder_file_entries(pratica_categoria):
    cartella = (pratica_categoria.cartella or "").strip()

    pratica_categoria.cartella_is_link = False
    pratica_categoria.cartella_is_folder = False
    pratica_categoria.cartella_error = ""
    pratica_categoria.file_entries = []

    if not cartella:
        return

    if is_external_link(cartella):
        pratica_categoria.cartella_is_link = True
        return

    folder_path = Path(cartella).expanduser()

    if not folder_path.exists():
        pratica_categoria.cartella_error = "Cartella non trovata"
        return

    if not folder_path.is_dir():
        pratica_categoria.cartella_error = "Il percorso non è una cartella"
        return

    pratica_categoria.cartella_is_folder = True
    pratica_categoria.file_entries = get_supported_file_entries(folder_path, pratica_categoria)


def save_category_formset_attachments(request, formset):
    for form in formset.forms:
        if not hasattr(form, "cleaned_data") or not form.cleaned_data:
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        pratica_categoria = form.instance

        if not pratica_categoria.pk:
            continue

        uploaded_files = request.FILES.getlist(f"{form.prefix}-allegato_file")

        for uploaded_file in uploaded_files:
            PraticaCategoriaAllegato.objects.create(
                pratica_categoria=pratica_categoria,
                file=uploaded_file,
                descrizione=(request.POST.get(f"{form.prefix}-allegato_descrizione") or "").strip(),
                created_by=request.user,
                updated_by=request.user,
            )

        for relative_file in request.POST.getlist(f"{form.prefix}-scollega_files"):
            relative_file = (relative_file or "").strip()

            if not relative_file:
                continue

            metadata, created = PraticaCategoriaFile.objects.update_or_create(
                pratica_categoria=pratica_categoria,
                percorso_relativo=relative_file,
                is_active=True,
                defaults={
                    "scollegato": True,
                    "updated_by": request.user,
                },
            )

            if created:
                metadata.created_by = request.user
                metadata.save(update_fields=["created_by", "updated_at"])


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


def with_next(url, next_url):
    if not next_url:
        return url

    return f"{url}?{urlencode({'next': next_url})}"


def redirect_documento_scaduto(request, cliente, return_url=""):
    messages.warning(request, documento_scaduto_message(cliente))
    update_url = reverse("anagrafiche:anagrafica_update", kwargs={"pk": cliente.pk})
    params = {"prezioso": "1", "documento_scaduto": "1"}
    if return_url:
        params["next"] = return_url
    return redirect(f"{update_url}?{urlencode(params)}")


def wants_json_response(request):
    accept = request.headers.get("Accept", "")
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in accept
    )


def form_first_error_message(form):
    if form.non_field_errors():
        return str(form.non_field_errors()[0])
    for field_name, errors in form.errors.items():
        if not errors:
            continue
        if field_name == "__all__":
            return str(errors[0])
        field = form.fields.get(field_name)
        label = field.label if field is not None else field_name
        return f"{label}: {errors[0]}"
    return "Controlla i campi del form."


def documento_scaduto_json_response(request, cliente, return_url=""):
    update_url = reverse("anagrafiche:anagrafica_update", kwargs={"pk": cliente.pk})
    params = {"prezioso": "1", "documento_scaduto": "1"}
    if return_url:
        params["next"] = return_url
    return JsonResponse(
        {
            "ok": False,
            "message": documento_scaduto_message(cliente),
            "redirect_url": f"{update_url}?{urlencode(params)}",
        },
        status=400,
    )


def notify_gs_articolo_sync(request, pratica):
    """Sincronizza GS in background così Salva non resta bloccato sul redirect."""
    from threading import Thread

    pratica_id = pratica.pk
    user_id = getattr(request.user, "pk", None)

    def _run():
        from django.contrib.auth import get_user_model
        from django.db import close_old_connections

        close_old_connections()
        try:
            pratica_obj = Pratica.objects.filter(pk=pratica_id, is_active=True).first()
            if not pratica_obj:
                return
            user = None
            if user_id:
                user = get_user_model().objects.filter(pk=user_id).first()
            sync_pratica_to_gs_articoli(pratica_obj, user)
        except Exception:
            pass
        finally:
            close_old_connections()

    Thread(target=_run, daemon=True, name=f"gs-sync-{pratica_id}").start()
    return None


class PraticaListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = Pratica
    template_name = "pratiche/pratica_list.html"
    context_object_name = "pratiche"
    paginate_by = 20

    ATTENZIONE_NON_RITIRATE = "non_ritirate"
    ATTENZIONE_RITARDO_LAVORAZIONE = "ritardo_lavorazione"
    ATTENZIONE_CHOICES = {
        ATTENZIONE_NON_RITIRATE: "Non ritirate",
        ATTENZIONE_RITARDO_LAVORAZIONE: "Ritardo lavorazione",
    }

    def get_cliente_id(self):
        cliente_pk = self.kwargs.get("cliente_pk")
        if cliente_pk:
            return str(cliente_pk)
        return (self.request.GET.get("cliente") or "").strip()

    def get_attenzione(self):
        value = (self.request.GET.get("attenzione") or "").strip()
        if value in self.ATTENZIONE_CHOICES:
            return value
        return ""

    def get_negozio_filter(self):
        return resolve_negozio_filter(
            self.request.GET.get("negozio"),
            self.request.session.get("negozio"),
        )

    def filter_by_negozio(self, queryset):
        return apply_negozio_queryset_filter(queryset, self.get_negozio_filter())

    @staticmethod
    def base_attenzione_queryset():
        return Pratica.objects.filter(is_active=True, data_scadenza__isnull=False)

    def queryset_non_ritirate(self, today=None):
        today = today or timezone.localdate()
        queryset = Pratica.objects.filter(is_active=True).filter(
            Q(stato=Pratica.Stato.NON_RITIRATA)
            | Q(
                stato=Pratica.Stato.IN_CONSEGNA,
                data_scadenza__isnull=False,
                data_scadenza__lt=today,
            )
        )
        return self.filter_by_negozio(queryset)

    def queryset_ritardo_lavorazione(self, today=None):
        today = today or timezone.localdate()
        queryset = self.base_attenzione_queryset().filter(
            data_scadenza__lt=today,
        ).exclude(
            stato=Pratica.Stato.IN_CONSEGNA,
        ).exclude(
            stato__in={
                Pratica.Stato.COMPLETATA,
                Pratica.Stato.EVASA,
                Pratica.Stato.ANNULLATA,
                Pratica.Stato.ARCHIVIATA,
                Pratica.Stato.NON_RITIRATA,
            }
        )
        return self.filter_by_negozio(queryset)

    def get_queryset(self):
        queryset = (
            Pratica.objects.filter(is_active=True)
            .select_related(
                "cliente",
                "operatore",
                "riparatore",
                "centro_assistenza",
                "tipo_oggetto",
            )
            .only(
                "id",
                "codice",
                "negozio",
                "priorita",
                "stato",
                "tipologia",
                "titolo",
                "descrizione",
                "data_apertura",
                "data_scadenza",
                "prezzo_al",
                "referente_cognome",
                "referente_nome",
                "referente_telefono",
                "referente_cellulare",
                "referente_email",
                "cliente_id",
                "operatore_id",
                "riparatore_id",
                "centro_assistenza_id",
                "tipo_oggetto_id",
                "cliente__id",
                "cliente__cognome",
                "cliente__nome",
                "cliente__ragione_sociale",
                "operatore__id",
                "operatore__nominativo",
                "riparatore__id",
                "riparatore__denominazione",
                "centro_assistenza__id",
                "centro_assistenza__ragione_sociale",
                "tipo_oggetto__id",
                "tipo_oggetto__denominazione",
            )
        )
        queryset = self.filter_by_negozio(queryset)

        q = (self.request.GET.get("q") or "").strip()
        stato = self.request.GET.get("stato") or ""
        priorita = self.request.GET.get("priorita") or ""
        tipologia = self.request.GET.get("tipologia") or ""
        tipo_oggetto = self.request.GET.get("tipo_oggetto") or ""
        cliente_id = self.get_cliente_id()
        attenzione = self.get_attenzione()
        needs_distinct = False
        today = timezone.localdate()

        if attenzione == self.ATTENZIONE_NON_RITIRATE:
            queryset = queryset.filter(
                Q(stato=Pratica.Stato.NON_RITIRATA)
                | Q(
                    stato=Pratica.Stato.IN_CONSEGNA,
                    data_scadenza__isnull=False,
                    data_scadenza__lt=today,
                )
            )
            stato = ""
        elif attenzione == self.ATTENZIONE_RITARDO_LAVORAZIONE:
            queryset = queryset.filter(
                data_scadenza__isnull=False,
                data_scadenza__lt=today,
            ).exclude(
                stato=Pratica.Stato.IN_CONSEGNA,
            ).exclude(
                stato__in={
                    Pratica.Stato.COMPLETATA,
                    Pratica.Stato.EVASA,
                    Pratica.Stato.ANNULLATA,
                    Pratica.Stato.ARCHIVIATA,
                    Pratica.Stato.NON_RITIRATA,
                }
            )
            stato = ""

        if q:
            search_filter = (
                Q(codice__icontains=q)
                | Q(titolo__icontains=q)
                | Q(tipo_oggetto__denominazione__icontains=q)
                | Q(riparatore__denominazione__icontains=q)
                | Q(operatore__nominativo__icontains=q)
                | Q(cliente__ragione_sociale__icontains=q)
                | Q(cliente__cognome__icontains=q)
                | Q(cliente__nome__icontains=q)
                | Q(referente_cognome__icontains=q)
                | Q(referente_nome__icontains=q)
            )
            if len(q) >= 3:
                search_filter |= Q(categoria_collegamenti__categoria__denominazione__icontains=q)
                search_filter |= Q(
                    macro_categoria_collegamenti__macro_categoria__denominazione__icontains=q
                )
                needs_distinct = True
            queryset = queryset.filter(search_filter)

        if stato:
            queryset = queryset.filter(stato=stato)

        if priorita:
            queryset = queryset.filter(priorita=priorita)

        if tipologia in {choice.value for choice in Pratica.Tipologia}:
            queryset = queryset.filter(tipologia=tipologia)

        if tipo_oggetto:
            try:
                queryset = queryset.filter(tipo_oggetto_id=int(tipo_oggetto))
            except (TypeError, ValueError):
                pass

        if cliente_id:
            try:
                queryset = queryset.filter(cliente_id=int(cliente_id))
            except (TypeError, ValueError):
                pass

        if attenzione:
            queryset = queryset.order_by("data_scadenza", "id")
        else:
            queryset = queryset.order_by("-data_apertura", "-id")
        if needs_distinct:
            queryset = queryset.distinct()
        return queryset

    def get_tipi_oggetto_filtro(self):
        return TipoOggetto.objects.filter(is_active=True).order_by("denominazione")

    def build_active_filters(self, cliente_filtro):
        active_filters = []
        negozio_filter = self.get_negozio_filter()
        if negozio_filter == NEGOZIO_FILTER_ALL:
            active_filters.append(("Negozio", "Tutti i negozi"))
        else:
            active_filters.append(("Negozio", negozio_label(negozio_filter) or negozio_filter))

        attenzione = self.get_attenzione()
        if attenzione:
            active_filters.append(
                ("Attenzione", self.ATTENZIONE_CHOICES.get(attenzione, attenzione))
            )

        q = (self.request.GET.get("q") or "").strip()
        if q:
            active_filters.append(("Ricerca", q))

        if cliente_filtro:
            active_filters.append(("Cliente", cliente_filtro.display_name))

        tipo_oggetto_id = self.request.GET.get("tipo_oggetto") or ""
        if tipo_oggetto_id:
            tipo = TipoOggetto.objects.filter(pk=tipo_oggetto_id).values_list("denominazione", flat=True).first()
            if tipo:
                active_filters.append(("Tipo oggetto", tipo))

        tipologia = self.request.GET.get("tipologia") or ""
        if tipologia:
            active_filters.append(
                ("Tipologia", dict(Pratica.Tipologia.choices).get(tipologia, tipologia))
            )

        if not attenzione:
            stato = self.request.GET.get("stato") or ""
            if stato:
                active_filters.append(("Stato", dict(Pratica.Stato.choices).get(stato, stato)))

        priorita = self.request.GET.get("priorita") or ""
        if priorita:
            active_filters.append(("Priorita", dict(Pratica.Priorita.choices).get(priorita, priorita)))

        return active_filters

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stati"] = [
            (stato.value, stato.label) for stato in Pratica.STATI_SELEZIONABILI
        ]
        context["priorita"] = Pratica.Priorita.choices
        context["tipologie"] = Pratica.Tipologia.choices
        context["tipi_oggetto"] = self.get_tipi_oggetto_filtro()
        context["negozi"] = NEGOZI
        negozio_filter = self.get_negozio_filter()
        context["negozio_filter"] = negozio_filter
        context["negozio_filter_all"] = negozio_filter == NEGOZIO_FILTER_ALL
        context["negozio_filter_label"] = negozio_label(negozio_filter)
        cliente_id = self.get_cliente_id()
        context["selected_cliente"] = cliente_id
        context["cliente_filtro"] = None
        if cliente_id:
            context["cliente_filtro"] = Anagrafica.objects.filter(
                pk=cliente_id,
                is_active=True,
                tipo=Anagrafica.Tipo.CLIENTE,
            ).only("id", "cognome", "nome", "ragione_sociale").first()
        attenzione = self.get_attenzione()
        context["attenzione"] = attenzione
        context["count_non_ritirate"] = self.queryset_non_ritirate().count()
        context["count_ritardo_lavorazione"] = self.queryset_ritardo_lavorazione().count()
        if attenzione:
            mailto_oggetto = get_mailto_oggetto_template()
            mailto_corpo = get_mailto_corpo_template()
            for pratica in context["pratiche"]:
                pratica.mailto_href = build_mailto_href(
                    pratica.referente_email,
                    pratica,
                    oggetto_template=mailto_oggetto,
                    corpo_template=mailto_corpo,
                )
                pratica.mailto_register_url = reverse(
                    "pratiche:comunicazione_mailto_register",
                    kwargs={"pratica_pk": pratica.pk},
                )
        context["active_filters"] = self.build_active_filters(context["cliente_filtro"])
        query_dict = self.request.GET.copy()
        query_dict.pop("page", None)
        if "negozio" not in query_dict:
            query_dict["negozio"] = negozio_filter
        context["filters_query"] = query_dict.urlencode()
        return context

class PraticaDetailView(LoginRequiredMixin, DetailView):
    model = Pratica
    template_name = "pratiche/pratica_detail.html"
    context_object_name = "pratica"
    queryset = Pratica.objects.select_related(
        "cliente",
        "responsabile",
        "operatore",
        "tipo_oggetto",
        "riparatore",
        "centro_assistenza",
    ).prefetch_related(
        Prefetch(
            "foto",
            queryset=PraticaFoto.objects.filter(is_active=True).order_by("created_at", "id"),
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["eventi_agenda"] = self.object.eventi_agenda.filter(is_active=True).order_by(
            "data_inizio",
            "ora_inizio",
        )[:8]
        context["comunicazioni"] = self.object.comunicazioni.filter(is_active=True).order_by("-data_ora", "-id")
        context["comunicazione_form"] = ComunicazionePraticaForm(
            formato_data=get_comunicazioni_formato_data()
        )
        context["return_url"] = get_safe_next_url(self.request) or reverse("pratiche:pratica_list")
        context["return_label"] = "Anagrafica" if get_safe_next_url(self.request) else "Elenco"
        context["next_url"] = get_safe_next_url(self.request)
        return context


class PraticaBustaPrintView(LoginRequiredMixin, DetailView):
    model = Pratica
    template_name = "pratiche/pratica_busta_print.html"
    context_object_name = "pratica"

    def get_queryset(self):
        return Pratica.objects.filter(is_active=True).select_related(
            "cliente",
            "operatore",
            "tipo_oggetto",
            "riparatore",
            "centro_assistenza",
        )

    def get(self, request, *args, **kwargs):
        from django.template.loader import render_to_string
        from django.templatetags.static import static

        pratica = self.get_object()
        missing_scadenza_msg = (
            "Impossibile stampare la busta: inserisci la Data prevista consegna "
            "nella scheda riparazione."
        )
        fmt = (request.GET.get("format") or "").lower()

        if not pratica.data_scadenza:
            if fmt == "json":
                return JsonResponse(
                    {
                        "ok": False,
                        "message": missing_scadenza_msg,
                        "redirect_url": reverse("pratiche:pratica_update", args=[pratica.pk]),
                    },
                    status=400,
                )
            messages.error(request, missing_scadenza_msg)
            return redirect("pratiche:pratica_update", pk=pratica.pk)

        if fmt == "json":
            self.object = pratica
            context = self.get_context_data()
            sheet_html = render_to_string(
                "pratiche/partials/busta_sheet.html",
                context,
                request=request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "title": f"Busta riparazione · {pratica.codice}",
                    "sheet_html": sheet_html,
                    "css_url": request.build_absolute_uri(
                        static("securtek/css/busta_print.css")
                    )
                    + "?v=20260721-40",
                }
            )

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from apps.core.models import Azienda
        from apps.pratiche.busta import build_busta_context

        context = super().get_context_data(**kwargs)
        context["busta"] = build_busta_context(self.object)
        context["azienda"] = (
            Azienda.objects.filter(is_active=True).order_by("ragione_sociale").first()
        )
        return context


class PraticaPrivacyPrintView(LoginRequiredMixin, View):
    def get(self, request, pk):
        pratica = get_object_or_404(
            Pratica.objects.select_related("cliente", "tipo_oggetto").prefetch_related(
                "foto",
                "cliente__indirizzi",
            ),
            pk=pk,
            is_active=True,
        )

        from apps.pratiche.privacy import (
            build_privacy_pdf_bytes,
            privacy_pdf_filename,
            privacy_pdf_pages_as_png_data_uris,
        )

        try:
            pdf_bytes = build_privacy_pdf_bytes(pratica)
        except FileNotFoundError:
            messages.error(
                request,
                "Modello scheda privacy non trovato. Contatta l'amministratore.",
            )
            return redirect("pratiche:pratica_detail", pk=pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("pratiche:pratica_detail", pk=pk)

        filename = privacy_pdf_filename(pratica)
        pdf_url = (
            reverse("pratiche:pratica_privacy_print", args=[pratica.pk]) + "?format=pdf"
        )
        fmt = (request.GET.get("format") or "").lower()

        # PDF grezzo (iframe / download)
        if fmt == "pdf":
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            response["X-Frame-Options"] = "SAMEORIGIN"
            return response

        page_images = privacy_pdf_pages_as_png_data_uris(pdf_bytes)
        document_title = filename.replace(".pdf", "").replace("_", " ")
        cliente = pratica.cliente
        documento_scaduto = is_documento_identita_scaduto(cliente)
        documento_warning = (
            documento_scaduto_privacy_message(cliente) if documento_scaduto else ""
        )

        # Dati per modale (stampa senza aprire una scheda con URL visibile)
        if fmt == "json":
            return JsonResponse(
                {
                    "ok": True,
                    "filename": filename,
                    "title": document_title,
                    "pdf_url": pdf_url,
                    "page_images": page_images,
                    "documento_scaduto": documento_scaduto,
                    "documento_scaduto_warning": documento_warning,
                }
            )

        # Pagina dedicata (fallback diretto)
        return render(
            request,
            "pratiche/pratica_privacy_print.html",
            {
                "pratica": pratica,
                "filename": filename,
                "document_title": document_title,
                "pdf_url": pdf_url,
                "page_images": page_images,
                "documento_scaduto": documento_scaduto,
                "documento_scaduto_warning": documento_warning,
            },
        )


class ClienteReferenteJsonView(LoginRequiredMixin, View):
    def get(self, request, pk):
        referente = get_referente_from_cliente_id(pk)
        if referente is None:
            return JsonResponse({"error": "Cliente non trovato."}, status=404)
        return JsonResponse(referente)


def serialize_cliente_search_result(anagrafica):
    details = []
    if anagrafica.codice_fiscale:
        details.append(anagrafica.codice_fiscale)
    if anagrafica.telefono:
        details.append(anagrafica.telefono)
    elif anagrafica.cellulare:
        details.append(anagrafica.cellulare)

    return {
        "id": anagrafica.pk,
        "label": anagrafica.display_name,
        "subtitle": " · ".join(details),
    }


class ClienteSearchView(LoginRequiredMixin, View):
    def get(self, request):
        selected_id = (request.GET.get("selected") or "").strip()
        query = (request.GET.get("q") or "").strip()
        results = []
        seen_ids = set()

        if selected_id:
            selected = (
                Anagrafica.objects.filter(
                    pk=selected_id,
                    is_active=True,
                    tipo=Anagrafica.Tipo.CLIENTE,
                )
                .first()
            )
            if selected:
                results.append(serialize_cliente_search_result(selected))
                seen_ids.add(selected.pk)

        if len(query) >= 2:
            from apps.anagrafiche.search import (
                annotate_anagrafica_name_search,
                build_anagrafica_name_search_q,
            )

            queryset = (
                annotate_anagrafica_name_search(
                    Anagrafica.objects.filter(
                        is_active=True,
                        tipo=Anagrafica.Tipo.CLIENTE,
                    )
                )
                .filter(build_anagrafica_name_search_q(query, include_contacts=True))
                .order_by("cognome", "nome", "ragione_sociale")[:20]
            )
            for anagrafica in queryset:
                if anagrafica.pk in seen_ids:
                    continue
                results.append(serialize_cliente_search_result(anagrafica))

        return JsonResponse({"results": results})


class PraticaCreateView(LoginRequiredMixin, CreateView):
    model = Pratica
    form_class = PraticaForm
    template_name = "pratiche/pratica_form.html"

    def get_initial(self):
        initial = super().get_initial()
        cliente_id = self.request.GET.get("cliente")

        if cliente_id:
            initial["cliente"] = cliente_id
            referente = get_referente_from_cliente_id(cliente_id)
            if referente:
                initial.update(
                    {
                        "referente_nome": referente["nome"],
                        "referente_cognome": referente["cognome"],
                        "referente_telefono": referente["telefono"],
                        "referente_cellulare": referente["cellulare"],
                        "referente_email": referente["email"],
                    }
                )

        return initial

    def form_invalid(self, form):
        cliente = getattr(form, "documento_scaduto_cliente", None)
        if cliente:
            return_url = self.request.get_full_path()
            return redirect_documento_scaduto(self.request, cliente, return_url)
        return super().form_invalid(form)

    def form_valid(self, form):
        negozio = normalize_negozio_code(self.request.session.get("negozio"))
        if not negozio:
            messages.error(
                self.request,
                "Negozio non selezionato. Effettua nuovamente l'accesso.",
            )
            return redirect("accounts:login")

        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.negozio = negozio
        form.instance.codice = reserve_pratica_codice(
            negozio,
            self.request.POST.get("codice_riservato", ""),
        )
        if not form.instance.responsabile:
            form.instance.responsabile = self.request.user
        self.object = form.save()
        notify_gs_articolo_sync(self.request, self.object)
        saved_count = len(save_pratica_foto_uploads(self.request, self.object))
        messages.success(self.request, "Riparazione creata correttamente.")
        if saved_count:
            messages.success(
                self.request,
                f"{saved_count} foto collegata/e alla riparazione.",
            )
        return redirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["operatore_primo"] = operatore_primo_nuova_riparazione()
        kwargs["layout_compatto"] = layout_compatto(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["operatore_primo"] = operatore_primo_nuova_riparazione()
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        context["cancel_url"] = next_url or reverse("pratiche:pratica_list")
        negozio = normalize_negozio_code(self.request.session.get("negozio"))
        context["current_negozio_code"] = negozio
        context["preview_codice"] = get_next_pratica_codice(negozio) if negozio else ""
        context["cliente_referente_url_template"] = cliente_referente_url_template()
        context["pratica_foto"] = []
        return context

    def get_success_url(self):
        return reverse("pratiche:pratica_list")


class PraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = Pratica
    form_class = PraticaForm
    template_name = "pratiche/pratica_form.html"

    def get_queryset(self):
        return Pratica.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "foto",
                queryset=PraticaFoto.objects.filter(is_active=True).order_by("created_at", "id"),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["layout_compatto"] = layout_compatto(self.request)
        return kwargs

    def form_invalid(self, form):
        cliente = getattr(form, "documento_scaduto_cliente", None)
        if cliente:
            return_url = self.request.get_full_path()
            if wants_json_response(self.request):
                return documento_scaduto_json_response(self.request, cliente, return_url)
            return redirect_documento_scaduto(self.request, cliente, return_url)
        if wants_json_response(self.request):
            return JsonResponse(
                {
                    "ok": False,
                    "message": form_first_error_message(form),
                    "errors": form.errors.get_json_data(),
                },
                status=400,
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        self.object = form.save()
        delete_pratica_foto_ids(self.request, self.object)
        saved_count = len(save_pratica_foto_uploads(self.request, self.object))
        notify_gs_articolo_sync(self.request, self.object)
        if wants_json_response(self.request):
            return JsonResponse(
                {
                    "ok": True,
                    "message": "Scheda salvata.",
                    "saved_fotos": saved_count,
                }
            )
        messages.success(self.request, "Riparazione aggiornata correttamente.")
        if saved_count:
            messages.success(
                self.request,
                f"{saved_count} foto aggiunta/e alla riparazione.",
            )
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        context["cancel_url"] = next_url or reverse("pratiche:pratica_list")
        context["cliente_referente_url_template"] = cliente_referente_url_template()
        context["pratica_foto"] = list(self.object.foto.all())
        context["comunicazioni"] = self.object.comunicazioni.filter(is_active=True).order_by(
            "-data_ora",
            "-id",
        )
        context["comunicazione_form"] = ComunicazionePraticaForm(
            formato_data=get_comunicazioni_formato_data()
        )
        return context

    def get_success_url(self):
        return reverse("pratiche:pratica_list")


class PraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pk"], is_active=True)
        pratica.soft_delete(user=request.user)
        messages.success(request, "Riparazione eliminata correttamente.")
        return redirect("pratiche:pratica_list")


class PraticaFotoUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        saved = save_pratica_foto_uploads(request, pratica)

        if saved:
            messages.success(request, f"{len(saved)} foto aggiunta/e alla riparazione.")
        else:
            messages.warning(request, "Seleziona almeno una foto da aggiungere.")

        next_url = get_safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class PraticaFotoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        foto = get_object_or_404(
            PraticaFoto,
            pk=kwargs["pk"],
            pratica=pratica,
            is_active=True,
        )
        foto.soft_delete(user=request.user)
        messages.success(request, "Foto eliminata dalla riparazione.")

        next_url = get_safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class ComunicazionePraticaCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        form = ComunicazionePraticaForm(
            request.POST,
            request.FILES,
            formato_data=get_comunicazioni_formato_data(),
        )

        if form.is_valid():
            comunicazione = form.save(commit=False)
            comunicazione.pratica = pratica
            comunicazione.created_by = request.user
            comunicazione.updated_by = request.user
            comunicazione.save()
            messages.success(request, "Comunicazione registrata correttamente.")
        else:
            messages.error(request, "Controlla i dati della comunicazione.")

        next_url = get_safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class ComunicazionePraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        comunicazione = get_object_or_404(
            ComunicazionePratica,
            pk=kwargs["pk"],
            pratica=pratica,
            is_active=True,
        )
        comunicazione.soft_delete(user=request.user)
        messages.success(request, "Comunicazione eliminata correttamente.")

        next_url = get_safe_next_url(request)
        if next_url:
            return redirect(next_url)
        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class ComunicazionePraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = ComunicazionePratica
    form_class = ComunicazionePraticaForm
    template_name = "pratiche/comunicazione_form.html"
    context_object_name = "comunicazione"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return ComunicazionePratica.objects.filter(
            is_active=True,
            pratica_id=self.kwargs["pratica_pk"],
            pratica__is_active=True,
        ).select_related("pratica", "pratica__cliente")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["formato_data"] = get_comunicazioni_formato_data()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pratica = self.object.pratica
        context["pratica"] = pratica
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        context["cancel_url"] = next_url or (
            reverse("pratiche:pratica_update", kwargs={"pk": pratica.pk}) + "#comunicazioni"
        )
        return context

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Comunicazione aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        next_url = get_safe_next_url(self.request)
        if next_url:
            return next_url
        return reverse("pratiche:pratica_update", kwargs={"pk": self.object.pratica_id}) + "#comunicazioni"


class ComunicazioneMailtoRegisterView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(
            Pratica.objects.only(
                "id",
                "codice",
                "referente_nome",
                "referente_cognome",
                "referente_email",
                "referente_telefono",
                "referente_cellulare",
                "cliente_id",
            ).select_related("cliente"),
            pk=kwargs["pratica_pk"],
            is_active=True,
        )
        email = (pratica.referente_email or "").strip()
        if not email:
            return JsonResponse(
                {"ok": False, "message": "Nessuna email disponibile per questa riparazione."},
                status=400,
            )

        oggetto = format_mailto_oggetto(pratica)
        corpo = format_mailto_corpo(pratica)
        lines = [
            f"Mail inviata a {email}.",
            f"Oggetto: {oggetto}" if oggetto else "",
        ]
        if corpo:
            lines.extend(["", corpo])
        descrizione = "\n".join(line for line in lines if line is not None).strip()

        comunicazione = ComunicazionePratica(
            pratica=pratica,
            data_ora=timezone.now(),
            descrizione=descrizione,
            created_by=request.user,
            updated_by=request.user,
        )
        comunicazione.save()

        return JsonResponse(
            {
                "ok": True,
                "message": "Invio mail registrato nelle comunicazioni.",
                "comunicazione_id": comunicazione.pk,
            }
        )


class ComunicazionePraticaFileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        comunicazione = get_object_or_404(
            ComunicazionePratica,
            pk=kwargs["pk"],
            pratica_id=kwargs["pratica_pk"],
            is_active=True,
        )

        if not comunicazione.allegato:
            raise Http404("Allegato non disponibile")

        return FileResponse(
            comunicazione.allegato.open("rb"),
            as_attachment=False,
            filename=comunicazione.allegato_nome,
        )


class ComunicazionePraticaPreviewView(LoginRequiredMixin, DetailView):
    model = ComunicazionePratica
    template_name = "pratiche/comunicazione_preview.html"
    context_object_name = "comunicazione"

    def get_queryset(self):
        return ComunicazionePratica.objects.filter(
            pratica_id=self.kwargs["pratica_pk"],
            is_active=True,
        ).select_related("pratica", "pratica__cliente")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.object.allegato:
            raise Http404("Allegato non disponibile")

        if not self.object.allegato_nome.lower().endswith(".eml"):
            return redirect("pratiche:comunicazione_file", pratica_pk=self.object.pratica_id, pk=self.object.pk)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with self.object.allegato.open("rb") as file_obj:
            context["email_preview"] = extract_eml_preview(file_obj)

        return context


class CategoriaPraticaListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = CategoriaPratica
    template_name = "pratiche/categoria_pratica_list.html"
    context_object_name = "categorie"
    paginate_by = 20

    def get_queryset(self):
        queryset = CategoriaPratica.objects.filter(is_active=True).annotate(
            pratiche_attive=Count(
                "pratica_collegamenti",
                filter=Q(pratica_collegamenti__is_active=True, pratica_collegamenti__pratica__is_active=True),
                distinct=True,
            )
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(descrizione__icontains=q)
            )

        return queryset.order_by("denominazione")


class CategoriaPraticaCreateView(LoginRequiredMixin, CreateView):
    model = CategoriaPratica
    form_class = CategoriaPraticaForm
    template_name = "pratiche/categoria_pratica_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:categoria_pratica_list")


class CategoriaPraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = CategoriaPratica
    form_class = CategoriaPraticaForm
    template_name = "pratiche/categoria_pratica_form.html"

    def get_queryset(self):
        return CategoriaPratica.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:categoria_pratica_list")


class CategoriaPraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        categoria = get_object_or_404(CategoriaPratica, pk=kwargs["pk"], is_active=True)
        categoria.soft_delete(user=request.user)
        messages.success(request, "Categoria eliminata correttamente.")
        return redirect("pratiche:categoria_pratica_list")


class MacroCategoriaPraticaListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = MacroCategoriaPratica
    template_name = "pratiche/macro_categoria_pratica_list.html"
    context_object_name = "macro_categorie"
    paginate_by = 20

    def get_queryset(self):
        queryset = MacroCategoriaPratica.objects.filter(is_active=True).annotate(
            categorie_count=Count("categorie", filter=Q(categorie__is_active=True), distinct=True),
            pratiche_attive=Count(
                "pratica_collegamenti",
                filter=Q(pratica_collegamenti__is_active=True, pratica_collegamenti__pratica__is_active=True),
                distinct=True,
            ),
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(descrizione__icontains=q)
                | Q(categorie__denominazione__icontains=q)
            )

        return queryset.prefetch_related("categorie").order_by("denominazione").distinct()


class MacroCategoriaPraticaCreateView(LoginRequiredMixin, CreateView):
    model = MacroCategoriaPratica
    form_class = MacroCategoriaPraticaForm
    template_name = "pratiche/macro_categoria_pratica_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Macro-categoria creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:macro_categoria_pratica_list")


class MacroCategoriaPraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = MacroCategoriaPratica
    form_class = MacroCategoriaPraticaForm
    template_name = "pratiche/macro_categoria_pratica_form.html"

    def get_queryset(self):
        return MacroCategoriaPratica.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Macro-categoria aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:macro_categoria_pratica_list")


class MacroCategoriaPraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        macro_categoria = get_object_or_404(MacroCategoriaPratica, pk=kwargs["pk"], is_active=True)
        macro_categoria.soft_delete(user=request.user)
        messages.success(request, "Macro-categoria eliminata correttamente.")
        return redirect("pratiche:macro_categoria_pratica_list")


class PraticaMacroCategoriaApplyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        form = PraticaMacroCategoriaApplyForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Seleziona una macro-categoria valida.")
            return redirect("pratiche:pratica_detail", pk=pratica.pk)

        macro_categoria = form.cleaned_data["macro_categoria"]
        categorie = list(macro_categoria.categorie.filter(is_active=True))

        with transaction.atomic():
            collegamento, created = PraticaMacroCategoria.objects.get_or_create(
                pratica=pratica,
                macro_categoria=macro_categoria,
                is_active=True,
                defaults={
                    "created_by": request.user,
                    "updated_by": request.user,
                },
            )
            if not created:
                collegamento.updated_by = request.user
                collegamento.save(update_fields=["updated_by", "updated_at"])

            categorie_aggiunte = 0
            for categoria in categorie:
                _, categoria_created = PraticaCategoria.objects.get_or_create(
                    pratica=pratica,
                    macro_categoria=macro_categoria,
                    categoria=categoria,
                    versione="",
                    is_active=True,
                    defaults={
                        "created_by": request.user,
                        "updated_by": request.user,
                        "origine_template": False,
                    },
                )
                if categoria_created:
                    categorie_aggiunte += 1

        if categorie_aggiunte:
            messages.success(
                request,
                f"Macro-categoria collegata. Categorie aggiunte: {categorie_aggiunte}.",
            )
        else:
            messages.info(request, "Macro-categoria collegata. Le categorie erano gia' presenti nella riparazione.")

        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class PraticaCategoriaCreateView(LoginRequiredMixin, CreateView):
    model = PraticaCategoria
    form_class = PraticaCategoriaForm
    template_name = "pratiche/pratica_categoria_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pratica"] = self.pratica
        return kwargs

    def form_valid(self, form):
        form.instance.pratica = self.pratica
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria collegata correttamente.")
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(
                "versione",
                "Questa categoria e questa versione sono gia' collegate alla riparazione.",
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pratica"] = self.pratica
        context["page_title"] = "Collega categoria"
        return context

    def get_success_url(self):
        return reverse_lazy("pratiche:pratica_detail", kwargs={"pk": self.pratica.pk})


class PraticaCategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = PraticaCategoria
    form_class = PraticaCategoriaForm
    template_name = "pratiche/pratica_categoria_form.html"

    def get_queryset(self):
        return PraticaCategoria.objects.filter(pratica_id=self.kwargs["pratica_pk"], is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pratica"] = self.object.pratica
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria aggiornata correttamente.")
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(
                "versione",
                "Questa categoria e questa versione sono gia' collegate alla riparazione.",
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pratica"] = self.object.pratica
        context["page_title"] = "Modifica categoria riparazione"
        return context

    def get_success_url(self):
        return reverse_lazy("pratiche:pratica_detail", kwargs={"pk": self.object.pratica_id})


class PraticaCategoriaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_object_or_404(
            PraticaCategoria,
            pk=kwargs["pk"],
            pratica_id=kwargs["pratica_pk"],
            is_active=True,
        )
        pratica_pk = pratica_categoria.pratica_id
        pratica_categoria.soft_delete(user=request.user)
        messages.success(request, "Categoria rimossa dalla riparazione.")
        return redirect("pratiche:pratica_detail", pk=pratica_pk)


class PraticaCategoriaFileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        _, file_path = resolve_categoria_file_path(pratica_categoria, request.GET.get("file") or "")

        return FileResponse(file_path.open("rb"), as_attachment=False, filename=file_path.name)


class PraticaCategoriaFileOpenView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        _, file_path = resolve_categoria_file_path(pratica_categoria, request.GET.get("file") or "")
        return_url = get_safe_next_url(request) or (
            reverse("pratiche:pratica_detail", kwargs={"pk": pratica_categoria.pratica_id})
            + f"#category-detail-{pratica_categoria.pk}"
        )

        if file_path.suffix.lower() not in NATIVE_OPEN_EXTENSIONS:
            return redirect(return_url)

        try:
            open_with_default_application(file_path)
            messages.success(request, f"File aperto: {file_path.name}")
        except OSError as exc:
            messages.error(request, f"Impossibile aprire il file con l'applicazione originale: {exc}")

        return redirect(return_url)


class PraticaCategoriaFileUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        folder_path = get_pratica_categoria_folder_path(pratica_categoria)

        if not folder_path:
            messages.error(request, "Collega prima una cartella valida alla categoria.")
            return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])

        uploaded_files = request.FILES.getlist("file")
        description = (request.POST.get("descrizione") or "").strip()

        if not uploaded_files:
            messages.error(request, "Seleziona un file valido da aggiungere.")
            return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])

        added_count = 0

        for uploaded_file in uploaded_files:
            file_name = Path(uploaded_file.name).name

            if not file_name:
                messages.error(request, "Nome file non valido.")
                continue

            target_path = (folder_path / file_name).resolve()

            if folder_path not in target_path.parents:
                messages.error(request, f"Percorso file non valido: {file_name}")
                continue

            if target_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
                messages.error(request, f"Tipo file non supportato: {file_name}")
                continue

            if target_path.exists():
                messages.error(request, f"Esiste gia' un file con questo nome nella cartella: {file_name}")
                continue

            with target_path.open("wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            PraticaCategoriaFile.objects.update_or_create(
                pratica_categoria=pratica_categoria,
                percorso_relativo=file_name,
                is_active=True,
                defaults={
                    "descrizione": description,
                    "scollegato": False,
                    "created_by": request.user,
                    "updated_by": request.user,
                },
            )
            added_count += 1

        if added_count:
            messages.success(request, f"{added_count} file aggiunti correttamente.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaFileDescriptionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        relative_file = (request.POST.get("file") or "").strip()

        resolve_categoria_file_path(pratica_categoria, relative_file)

        metadata, created = PraticaCategoriaFile.objects.update_or_create(
            pratica_categoria=pratica_categoria,
            percorso_relativo=relative_file,
            is_active=True,
            defaults={
                "descrizione": (request.POST.get("descrizione") or "").strip(),
                "scollegato": False,
                "updated_by": request.user,
            },
        )

        if created:
            metadata.created_by = request.user
            metadata.save(update_fields=["created_by", "updated_at"])

        messages.success(request, "Descrizione file salvata.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaFileDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        relative_file = (request.POST.get("file") or "").strip()
        _, file_path = resolve_categoria_file_path(pratica_categoria, relative_file)

        file_path.unlink()
        metadata = PraticaCategoriaFile.objects.filter(
            pratica_categoria=pratica_categoria,
            percorso_relativo=relative_file,
            is_active=True,
        ).first()

        if metadata:
            metadata.soft_delete(user=request.user)

        messages.success(request, "File eliminato correttamente.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaFileUnlinkView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        relative_file = (request.POST.get("file") or "").strip()
        resolve_categoria_file_path(pratica_categoria, relative_file)

        metadata, created = PraticaCategoriaFile.objects.update_or_create(
            pratica_categoria=pratica_categoria,
            percorso_relativo=relative_file,
            is_active=True,
            defaults={
                "scollegato": True,
                "updated_by": request.user,
            },
        )

        if created:
            metadata.created_by = request.user
            metadata.save(update_fields=["created_by", "updated_at"])

        messages.success(request, "File scollegato dalla riparazione.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaAllegatoUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["categoria_pk"])
        uploaded_files = request.FILES.getlist("file")
        description = (request.POST.get("descrizione") or "").strip()

        if not uploaded_files:
            messages.error(request, "Seleziona un file valido da collegare.")
            return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])

        for uploaded_file in uploaded_files:
            PraticaCategoriaAllegato.objects.create(
                pratica_categoria=pratica_categoria,
                file=uploaded_file,
                descrizione=description,
                created_by=request.user,
                updated_by=request.user,
            )

        messages.success(request, f"{len(uploaded_files)} file singoli collegati correttamente.")
        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{pratica_categoria.pk}"
        )


class PraticaCategoriaAllegatoPickView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["categoria_pk"])

        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            messages.error(request, f"Selettore file non disponibile: {exc}")
            return redirect(
                reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
                + f"#category-detail-{pratica_categoria.pk}"
            )

        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected_path = filedialog.askopenfilename(
                title="Seleziona file da collegare",
                filetypes=[
                    ("File supportati", "*.doc *.docx *.xls *.xlsx *.xlsm *.pdf *.png *.jpg *.jpeg *.txt *.html *.htm"),
                    ("Tutti i file", "*.*"),
                ],
            )
            root.destroy()
        except Exception as exc:
            messages.error(request, f"Impossibile aprire il selettore file: {exc}")
            return redirect(
                reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
                + f"#category-detail-{pratica_categoria.pk}"
            )

        if selected_path:
            try:
                create_category_attachment_from_path(pratica_categoria, selected_path, request.user)
                messages.success(request, "File singolo collegato correttamente.")
            except ValueError as exc:
                messages.error(request, str(exc))

        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{pratica_categoria.pk}"
        )


class PraticaCategoriaAllegatoFileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )

        if not allegato.file:
            raise Http404("File non disponibile")

        return FileResponse(allegato.file.open("rb"), as_attachment=False, filename=allegato.file_nome)


class PraticaCategoriaAllegatoOpenView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )
        return_url = get_safe_next_url(request) or (
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{kwargs['categoria_pk']}"
        )

        if not allegato.file:
            return redirect(return_url)

        file_path = Path(allegato.file.path)

        if file_path.suffix.lower() not in NATIVE_OPEN_EXTENSIONS:
            return redirect(return_url)

        try:
            open_with_default_application(file_path)
            messages.success(request, f"File aperto: {allegato.file_nome}")
        except OSError as exc:
            messages.error(request, f"Impossibile aprire il file con l'applicazione originale: {exc}")

        return redirect(return_url)


class PraticaCategoriaAllegatoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )
        allegato.soft_delete(user=request.user)
        messages.success(request, "File singolo scollegato correttamente.")
        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{kwargs['categoria_pk']}"
        )


class PraticaCategoriaAllegatoDestroyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )

        if allegato.file:
            allegato.file.delete(save=False)

        allegato.soft_delete(user=request.user)
        messages.success(request, "File singolo eliminato correttamente.")
        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{kwargs['categoria_pk']}"
        )


class FolderPickerView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            return JsonResponse({"error": f"Selettore cartella non disponibile: {exc}"}, status=500)

        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected_path = filedialog.askdirectory(title="Seleziona cartella riparazione")
            root.destroy()
        except Exception as exc:
            return JsonResponse({"error": f"Impossibile aprire il selettore cartella: {exc}"}, status=500)

        if not selected_path:
            return JsonResponse({"path": ""})

        return JsonResponse({"path": selected_path})


class FolderPreviewView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        folder_value = (request.GET.get("path") or "").strip()

        if not folder_value:
            return JsonResponse({"files": [], "error": ""})

        if is_external_link(folder_value):
            return JsonResponse({"files": [], "is_link": True, "error": ""})

        folder_path = Path(folder_value).expanduser()

        if not folder_path.exists():
            return JsonResponse({"files": [], "error": "Cartella non trovata"})

        if not folder_path.is_dir():
            return JsonResponse({"files": [], "error": "Il percorso non è una cartella"})

        return JsonResponse({"files": get_supported_file_entries(folder_path), "error": ""})


class FolderPreviewFileOpenView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        _, file_path = resolve_preview_folder_file_path(
            request.GET.get("path") or "",
            request.GET.get("file") or "",
        )

        if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS:
            try:
                open_with_default_application(file_path)
                return JsonResponse({"opened": True, "message": f"File aperto: {file_path.name}"})
            except OSError as exc:
                return JsonResponse(
                    {"opened": False, "error": f"Impossibile aprire il file con l'applicazione originale: {exc}"},
                    status=500,
                )

        return FileResponse(file_path.open("rb"), as_attachment=False, filename=file_path.name)


class FolderPreviewFileDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        _, file_path = resolve_preview_folder_file_path(
            request.POST.get("path") or "",
            request.POST.get("file") or "",
        )
        file_path.unlink()
        return JsonResponse({"deleted": True, "message": f"File eliminato: {file_path.name}"})


class StudioTecnicoListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = StudioTecnico
    template_name = "pratiche/studio_tecnico_list.html"
    context_object_name = "studi_tecnici"
    paginate_by = 20

    def get_queryset(self):
        queryset = StudioTecnico.objects.filter(is_active=True).annotate(
            pratiche_attive=Count(
                "pratiche_riparazione",
                filter=Q(pratiche_riparazione__is_active=True),
                distinct=True,
            ),
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(email__icontains=q)
                | Q(telefono__icontains=q)
            )

        return queryset.order_by("denominazione")


class StudioTecnicoCreateView(LoginRequiredMixin, CreateView):
    model = StudioTecnico
    form_class = StudioTecnicoForm
    template_name = "pratiche/studio_tecnico_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Riparatore creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:studio_tecnico_list")


class StudioTecnicoUpdateView(LoginRequiredMixin, UpdateView):
    model = StudioTecnico
    form_class = StudioTecnicoForm
    template_name = "pratiche/studio_tecnico_form.html"

    def get_queryset(self):
        return StudioTecnico.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Riparatore aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:studio_tecnico_list")


class StudioTecnicoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        studio = get_object_or_404(StudioTecnico, pk=kwargs["pk"], is_active=True)
        studio.soft_delete(user=request.user)
        messages.success(request, "Riparatore eliminato correttamente.")
        return redirect("pratiche:studio_tecnico_list")


class OperatoreListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = Operatore
    template_name = "pratiche/operatore_list.html"
    context_object_name = "operatori"
    paginate_by = 20

    def get_queryset(self):
        queryset = Operatore.objects.filter(is_active=True).annotate(
            riparazioni_attive=Count(
                "riparazioni",
                filter=Q(riparazioni__is_active=True),
                distinct=True,
            )
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(nominativo__icontains=q)

        return queryset.order_by("nominativo")


class OperatoreCreateView(LoginRequiredMixin, CreateView):
    model = Operatore
    form_class = OperatoreForm
    template_name = "pratiche/operatore_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Operatore creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:operatore_list")


class OperatoreUpdateView(LoginRequiredMixin, UpdateView):
    model = Operatore
    form_class = OperatoreForm
    template_name = "pratiche/operatore_form.html"

    def get_queryset(self):
        return Operatore.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Operatore aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:operatore_list")


class OperatoreDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        operatore = get_object_or_404(Operatore, pk=kwargs["pk"], is_active=True)
        operatore.soft_delete(user=request.user)
        messages.success(request, "Operatore eliminato correttamente.")
        return redirect("pratiche:operatore_list")


class TipoOggettoListView(LoginRequiredMixin, ConfigurablePaginationMixin, ListView):
    model = TipoOggetto
    template_name = "pratiche/tipo_oggetto_list.html"
    context_object_name = "tipi_oggetto"
    paginate_by = 20

    def get_queryset(self):
        queryset = TipoOggetto.objects.filter(is_active=True).annotate(
            pratiche_attive=Count(
                "pratiche",
                filter=Q(pratiche__is_active=True),
                distinct=True,
            )
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(descrizione__icontains=q)
            )

        return queryset.order_by("denominazione")


class TipoOggettoCreateView(LoginRequiredMixin, CreateView):
    model = TipoOggetto
    form_class = TipoOggettoForm
    template_name = "pratiche/tipo_oggetto_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Tipo oggetto creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:tipo_oggetto_list")


class TipoOggettoUpdateView(LoginRequiredMixin, UpdateView):
    model = TipoOggetto
    form_class = TipoOggettoForm
    template_name = "pratiche/tipo_oggetto_form.html"

    def get_queryset(self):
        return TipoOggetto.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Tipo oggetto aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:tipo_oggetto_list")


class TipoOggettoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        tipo_oggetto = get_object_or_404(TipoOggetto, pk=kwargs["pk"], is_active=True)
        tipo_oggetto.soft_delete(user=request.user)
        messages.success(request, "Tipo oggetto eliminato correttamente.")
        return redirect("pratiche:tipo_oggetto_list")

