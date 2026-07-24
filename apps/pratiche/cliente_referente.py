from django.urls import reverse

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo


def _pick_contatto(anagrafica, tipo):
    contatto = (
        anagrafica.contatti.filter(is_active=True, tipo=tipo)
        .order_by("-principale", "id")
        .first()
    )
    return contatto.valore if contatto else ""


def _format_date(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


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
            "data_nascita": _format_date(anagrafica.data_nascita),
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


def cliente_referente_url_template():
    from django.urls import reverse

    return reverse("pratiche:cliente_referente_json", kwargs={"pk": 0}).replace(
        "/0/", "/__CLIENTE_ID__/"
    )
