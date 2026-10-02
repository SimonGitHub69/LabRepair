from django.urls import reverse

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.pratiche.cliente_documento import is_documento_identita_scaduto


def _pick_contatto(anagrafica, tipo):
    contatto = (
        anagrafica.contatti.filter(is_active=True, tipo=tipo)
        .order_by("-principale", "id")
        .first()
    )
    return contatto.valore if contatto else ""


def _format_date(value, full_year=False):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y" if full_year else "%d/%m/%y")


def _format_date_iso(value):
    if not value:
        return ""
    return value.isoformat()


def _get_residenza(anagrafica):
    indirizzi = anagrafica.indirizzi.filter(is_active=True)
    residenza = (
        indirizzi.filter(tipo=Indirizzo.TipoIndirizzo.RESIDENZA)
        .order_by("-principale", "id")
        .first()
    )
    if residenza:
        return residenza
    principale = indirizzi.filter(principale=True).order_by("id").first()
    if principale:
        return principale
    return indirizzi.order_by("id").first()


def _format_indirizzo(indirizzo):
    if not indirizzo:
        return {
            "via": "",
            "cap": "",
            "comune": "",
            "provincia": "",
            "label": "",
        }

    via_parts = [
        part.strip()
        for part in [indirizzo.indirizzo, indirizzo.civico]
        if (part or "").strip()
    ]
    via = " ".join(via_parts)
    cap = (indirizzo.cap or "").strip()
    comune = (indirizzo.comune or "").strip()
    provincia = (indirizzo.provincia or "").strip()
    city = f"{comune} ({provincia})" if comune and provincia else (comune or provincia)
    label_parts = [part for part in [via, cap, city] if part]
    return {
        "via": via,
        "cap": cap,
        "comune": comune,
        "provincia": provincia,
        "label": " - ".join(label_parts),
    }


def get_referente_from_cliente(anagrafica):
    if not anagrafica:
        return {
            "nome": "",
            "cognome": "",
            "telefono": "",
            "cellulare": "",
            "email": "",
            "anagrafica": None,
        }

    telefono = anagrafica.telefono or _pick_contatto(anagrafica, Contatto.TipoContatto.TELEFONO)
    cellulare = anagrafica.cellulare or _pick_contatto(anagrafica, Contatto.TipoContatto.CELLULARE)
    email = anagrafica.email or _pick_contatto(anagrafica, Contatto.TipoContatto.EMAIL)
    indirizzo = _format_indirizzo(_get_residenza(anagrafica))
    documento_scaduto = is_documento_identita_scaduto(anagrafica)

    return {
        "nome": anagrafica.nome or "",
        "cognome": anagrafica.cognome or "",
        "telefono": telefono,
        "cellulare": cellulare,
        "email": email,
        "anagrafica": {
            "id": anagrafica.pk,
            "display_name": anagrafica.display_name,
            "cognome": anagrafica.cognome or "",
            "nome": anagrafica.nome or "",
            "sesso": anagrafica.get_sesso_display() if anagrafica.sesso else "",
            "codice_fiscale": anagrafica.codice_fiscale or "",
            "data_nascita": _format_date(anagrafica.data_nascita, full_year=True),
            "luogo_nascita": anagrafica.luogo_nascita or "",
            "provincia_nascita": anagrafica.provincia_nascita or "",
            "telefono": telefono,
            "cellulare": cellulare,
            "email": email,
            "documento_tipo": anagrafica.documento_tipo_label or anagrafica.documento_tipo or "",
            "documento_numero": anagrafica.documento_numero or "",
            "documento_rilasciato_da": anagrafica.documento_rilasciato_da or "",
            "documento_data_rilascio": _format_date(anagrafica.documento_data_rilascio),
            "documento_data_scadenza": _format_date(anagrafica.documento_data_scadenza),
            "documento_data_rilascio_iso": _format_date_iso(anagrafica.documento_data_rilascio),
            "documento_data_scadenza_iso": _format_date_iso(anagrafica.documento_data_scadenza),
            "stampa_privacy": bool(anagrafica.stampa_privacy),
            "documento_scaduto": documento_scaduto,
            "residenza": indirizzo["label"],
            "residenza_via": indirizzo["via"],
            "residenza_cap": indirizzo["cap"],
            "residenza_comune": indirizzo["comune"],
            "residenza_provincia": indirizzo["provincia"],
            "edit_url": reverse(
                "anagrafiche:anagrafica_update",
                kwargs={"pk": anagrafica.pk},
            )
            + "?tipo=cliente&prezioso=1",
            "documento_update_url": reverse(
                "anagrafiche:documento_update",
                kwargs={"pk": anagrafica.pk},
            ),
        },
    }


def get_referente_from_cliente_id(cliente_id):
    anagrafica = (
        Anagrafica.objects.filter(
            pk=cliente_id,
            is_active=True,
            tipo=Anagrafica.Tipo.CLIENTE,
        )
        .prefetch_related("contatti", "indirizzi")
        .first()
    )
    if not anagrafica:
        return None
    return get_referente_from_cliente(anagrafica)


def sync_referente_telefoni_to_cliente(pratica):
    """Copia telefono/cellulare/email della riparazione sull'anagrafica cliente collegata."""
    cliente = getattr(pratica, "cliente", None)
    if not cliente:
        return False

    telefono = (getattr(pratica, "referente_telefono", None) or "").strip()
    cellulare = (getattr(pratica, "referente_cellulare", None) or "").strip()
    email = (getattr(pratica, "referente_email", None) or "").strip()
    if not telefono and not cellulare and not email:
        return False

    update_fields = []
    if telefono and telefono != (cliente.telefono or "").strip():
        cliente.telefono = telefono
        update_fields.append("telefono")
    if cellulare and cellulare != (cliente.cellulare or "").strip():
        cliente.cellulare = cellulare
        update_fields.append("cellulare")
    if email and email != (cliente.email or "").strip():
        cliente.email = email
        update_fields.append("email")

    if not update_fields:
        return False

    cliente.save(update_fields=update_fields)
    return True


def ensure_cliente_from_referente(pratica, *, user=None):
    """
    Se la riparazione ha Cognome+Nome ma nessun cliente, crea (o riusa) l'anagrafica
    e la collega. Aggiorna comunque telefono/cellulare/email sul cliente.
    """
    if not pratica or not getattr(pratica, "pk", None):
        return None

    cognome = (getattr(pratica, "referente_cognome", None) or "").strip().upper()
    nome_raw = (getattr(pratica, "referente_nome", None) or "").strip()
    nome = " ".join(
        (part[:1].upper() + part[1:].lower()) if part else ""
        for part in nome_raw.split()
    )
    telefono = (getattr(pratica, "referente_telefono", None) or "").strip()
    cellulare = (getattr(pratica, "referente_cellulare", None) or "").strip()
    email = (getattr(pratica, "referente_email", None) or "").strip()

    if pratica.cliente_id:
        sync_referente_telefoni_to_cliente(pratica)
        return pratica.cliente

    if not cognome or not nome:
        return None

    cliente = (
        Anagrafica.objects.filter(
            is_active=True,
            tipo=Anagrafica.Tipo.CLIENTE,
            cognome__iexact=cognome,
            nome__iexact=nome,
        )
        .order_by("id")
        .first()
    )
    created = False
    if not cliente:
        cliente = Anagrafica(
            tipo=Anagrafica.Tipo.CLIENTE,
            cognome=cognome,
            nome=nome,
            telefono=telefono,
            cellulare=cellulare,
            email=email,
            is_active=True,
        )
        if user is not None:
            cliente.created_by = user
            cliente.updated_by = user
        cliente.save()
        created = True

    pratica.cliente = cliente
    pratica.save(update_fields=["cliente", "updated_at"])
    if not created:
        sync_referente_telefoni_to_cliente(pratica)
    return cliente


def cliente_referente_url_template():
    return reverse("pratiche:cliente_referente_json", kwargs={"pk": 0}).replace(
        "/0/", "/__CLIENTE_ID__/"
    )
