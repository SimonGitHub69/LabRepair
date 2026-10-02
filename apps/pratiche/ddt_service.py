from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.anagrafiche.models import Anagrafica, Indirizzo
from apps.core.negozi import get_negozio_ddt_settings, normalize_negozio_code
from apps.pratiche.models import Ddt, DdtRiga, Pratica

STATI_BUSTE_CHIUSE = {
    Pratica.Stato.EVASA,
    Pratica.Stato.COMPLETATA,
    Pratica.Stato.ANNULLATA,
    Pratica.Stato.ARCHIVIATA,
}

DDT_SEZIONALE_DEFAULT = "R"
DDT_CAUSALE_DEFAULT = "C/RIPARAZIONE"
DDT_ASPETTO_DEFAULT = "SACCHETTO"
DDT_TRASPORTO_DEFAULT = "Vettore"
DDT_VETTORE_DEFAULT = "GLS"


def get_ddt_sezionale_default(negozio=None):
    sezionale, _iniziale = get_negozio_ddt_settings(negozio)
    return sezionale or DDT_SEZIONALE_DEFAULT


def get_ddt_numero_iniziale(negozio=None):
    _sezionale, iniziale = get_negozio_ddt_settings(negozio)
    return iniziale


def get_next_ddt_numero(sezionale=None, negozio=None):
    negozio = normalize_negozio_code(negozio)
    sezionale_default, iniziale = get_negozio_ddt_settings(negozio)
    sezionale = (sezionale or sezionale_default).strip().upper() or DDT_SEZIONALE_DEFAULT
    qs = Ddt.objects.filter(is_active=True, sezionale__iexact=sezionale)
    if negozio:
        qs = qs.filter(negozio=negozio)
    else:
        qs = qs.filter(negozio="")
    current = qs.aggregate(Max("numero"))["numero__max"] or 0
    next_number = max(current + 1, iniziale)
    return next_number, sezionale


def get_centro_assistenza_indirizzo(centro):
    if not centro:
        return None

    indirizzi = centro.indirizzi.filter(is_active=True)
    for tipo in (
        Indirizzo.TipoIndirizzo.SEDE_LEGALE,
        Indirizzo.TipoIndirizzo.SPEDIZIONE,
        Indirizzo.TipoIndirizzo.SEDE_OPERATIVA,
        Indirizzo.TipoIndirizzo.FATTURAZIONE,
    ):
        found = indirizzi.filter(tipo=tipo).order_by("-principale", "id").first()
        if found:
            return found

    principale = indirizzi.filter(principale=True).order_by("id").first()
    if principale:
        return principale
    return indirizzi.order_by("id").first()


def format_indirizzo_via(indirizzo):
    if not indirizzo:
        return ""
    parts = []
    if (indirizzo.indirizzo or "").strip():
        parts.append(indirizzo.indirizzo.strip())
    if (indirizzo.civico or "").strip():
        parts.append(indirizzo.civico.strip())
    return " ".join(parts)


def format_busta_articolo(pratica):
    return (pratica.codice or "").strip() or str(pratica.pk)


def format_busta_descrizione(pratica):
    cliente = (pratica.cliente_label or "").strip().upper()
    if cliente:
        return f"BUSTA {cliente}"
    return "BUSTA"


def buste_aperte_queryset(centro_assistenza_id=None, exclude_in_ddt=True):
    qs = (
        Pratica.objects.filter(is_active=True)
        .exclude(stato__in=STATI_BUSTE_CHIUSE)
        .select_related("cliente", "tipo_oggetto", "centro_assistenza")
        .order_by("codice", "id")
    )
    if centro_assistenza_id:
        qs = qs.filter(centro_assistenza_id=centro_assistenza_id)
    if exclude_in_ddt:
        qs = qs.filter(ddt_numero="")
        qs = qs.exclude(ddt_righe__is_active=True, ddt_righe__ddt__is_active=True)
    return qs.distinct()


def serialize_busta_for_ddt(pratica, *, extra=False):
    cliente = (pratica.cliente_label or "").upper()
    centro = ""
    if pratica.centro_assistenza_id and pratica.centro_assistenza:
        centro = pratica.centro_assistenza.ragione_sociale or ""
    return {
        "id": pratica.pk,
        "codice": pratica.codice,
        "cliente": pratica.cliente_label,
        "stato": pratica.get_stato_display(),
        "oggetto": pratica.titolo or "",
        "peso": str(pratica.peso_grammi or 0),
        "articolo": (pratica.codice or "").strip(),
        "descrizione": f"BUSTA {cliente}".strip() if cliente else "BUSTA",
        "centro": centro,
        "extra": bool(extra),
    }


def find_busta_aperta_by_codice(codice, exclude_in_ddt=True):
    """Trova busta per codice accettando o meno il trattino (P26-0015 / P260015)."""
    from django.db.models import Value
    from django.db.models.functions import Replace, Upper

    code = (codice or "").strip().upper()
    if not code:
        return None
    code_compact = code.replace("-", "").replace(" ", "")
    if not code_compact:
        return None

    qs = buste_aperte_queryset(exclude_in_ddt=exclude_in_ddt)
    found = qs.filter(codice__iexact=code).first()
    if found:
        return found
    # Varianti con/senza trattino o spazi
    return (
        qs.annotate(
            codice_compact=Replace(
                Replace(Upper("codice"), Value("-"), Value("")),
                Value(" "),
                Value(""),
            )
        )
        .filter(codice_compact=code_compact)
        .first()
    )


def parse_busta_codici(raw_value):
    text = (raw_value or "").replace(";", ",").replace("\n", ",")
    parts = []
    for chunk in text.replace(" ", ",").split(","):
        code = chunk.strip().upper()
        if code and code not in parts:
            parts.append(code)
    return parts


def centri_assistenza_con_buste_aperte():
    ids = (
        Pratica.objects.filter(
            is_active=True,
            centro_assistenza_id__isnull=False,
            ddt_numero="",
        )
        .exclude(stato__in=STATI_BUSTE_CHIUSE)
        .exclude(ddt_righe__is_active=True, ddt_righe__ddt__is_active=True)
        .values_list("centro_assistenza_id", flat=True)
        .distinct()
    )
    return Anagrafica.objects.filter(
        is_active=True,
        tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA,
        pk__in=ids,
    ).order_by("ragione_sociale")


def snapshot_destinatario_from_centro(centro):
    indirizzo = get_centro_assistenza_indirizzo(centro)
    return {
        "destinatario_ragione_sociale": (centro.ragione_sociale or "").strip(),
        "destinatario_indirizzo": format_indirizzo_via(indirizzo),
        "destinatario_cap": ((indirizzo.cap if indirizzo else "") or "").strip(),
        "destinatario_comune": ((indirizzo.comune if indirizzo else "") or "").strip(),
        "destinatario_provincia": ((indirizzo.provincia if indirizzo else "") or "").strip(),
        "destinatario_partita_iva": (centro.partita_iva or "").strip(),
        "destinatario_codice_fiscale": (centro.codice_fiscale or "").strip(),
        "destinatario_codice_cliente": (centro.codice_gestionale or "").strip(),
    }


@transaction.atomic
def create_ddt(
    *,
    centro_assistenza,
    pratiche,
    user=None,
    negozio=None,
    sezionale=None,
    data_documento=None,
    causale=None,
    aspetto_beni=None,
    trasporto_a_cura=None,
    vettore=None,
    peso_lordo_kg=None,
    colli=None,
    data_inizio_trasporto=None,
    ora_inizio_trasporto=None,
    destinazione_merce="",
    agente="",
    note="",
):
    if not centro_assistenza or centro_assistenza.tipo != Anagrafica.Tipo.CENTRO_ASSISTENZA:
        raise ValueError("Seleziona un centro assistenza valido.")

    pratiche = list(pratiche)
    if not pratiche:
        raise ValueError("Seleziona almeno una busta aperta.")

    for pratica in pratiche:
        if pratica.stato in STATI_BUSTE_CHIUSE:
            raise ValueError(f"La riparazione {pratica.codice} non è una busta aperta.")
        if (pratica.ddt_numero or "").strip():
            raise ValueError(
                f"La riparazione {pratica.codice} ha già il DDT {pratica.ddt_numero}."
            )

    negozio = normalize_negozio_code(negozio)
    numero, sezionale = get_next_ddt_numero(sezionale, negozio=negozio)
    oggi = timezone.localdate()
    snapshot = snapshot_destinatario_from_centro(centro_assistenza)

    if peso_lordo_kg is None:
        peso_grammi = sum((Decimal(p.peso_grammi or 0) for p in pratiche), Decimal("0"))
        peso_lordo_kg = (peso_grammi / Decimal("1000")).quantize(Decimal("0.01"))

    ddt = Ddt(
        numero=numero,
        sezionale=sezionale,
        negozio=negozio,
        data_documento=data_documento or oggi,
        centro_assistenza=centro_assistenza,
        causale=(causale or DDT_CAUSALE_DEFAULT).strip() or DDT_CAUSALE_DEFAULT,
        aspetto_beni=(aspetto_beni or DDT_ASPETTO_DEFAULT).strip() or DDT_ASPETTO_DEFAULT,
        trasporto_a_cura=(trasporto_a_cura or DDT_TRASPORTO_DEFAULT).strip() or DDT_TRASPORTO_DEFAULT,
        vettore=(vettore or DDT_VETTORE_DEFAULT).strip() or DDT_VETTORE_DEFAULT,
        peso_lordo_kg=peso_lordo_kg,
        colli=colli if colli is not None else len(pratiche),
        data_inizio_trasporto=data_inizio_trasporto or oggi,
        ora_inizio_trasporto=ora_inizio_trasporto,
        destinazione_merce=(destinazione_merce or "").strip(),
        agente=(agente or "").strip(),
        note=(note or "").strip(),
        created_by=user,
        updated_by=user,
        **snapshot,
    )
    ddt.save()

    for index, pratica in enumerate(pratiche, start=1):
        DdtRiga.objects.create(
            ddt=ddt,
            pratica=pratica,
            ordine=index,
            articolo=format_busta_articolo(pratica),
            descrizione=format_busta_descrizione(pratica),
            unita_misura="NR",
            quantita=Decimal("1.00"),
            created_by=user,
            updated_by=user,
        )
        _apply_pratica_on_ddt_assign(pratica, ddt, user=user)

    return ddt


def buste_per_ddt_edit(ddt):
    """Solo le buste già presenti nel DDT (immutabili in modifica)."""
    current_ids = list(
        ddt.righe.filter(is_active=True).values_list("pratica_id", flat=True)
    )
    return (
        Pratica.objects.filter(pk__in=current_ids)
        .select_related("cliente", "tipo_oggetto", "centro_assistenza")
        .order_by("codice", "id")
    )


def _apply_pratica_on_ddt_assign(pratica, ddt, user=None):
    """Collega DDT alla busta e, se in Accettazione, passa a Riparatore + data riparatore."""
    update_fields = ["ddt_numero", "ddt_data", "updated_by", "updated_at"]
    pratica.ddt_numero = ddt.numero_display
    pratica.ddt_data = ddt.data_documento
    pratica.updated_by = user

    # Solo se ancora in Accettazione: non toccare stati già avanzati.
    if pratica.stato == Pratica.Stato.ACCETTAZIONE:
        pratica.stato = Pratica.Stato.RIPARATORE
        update_fields.append("stato")

    if not pratica.data_riparatore and ddt.data_documento:
        pratica.data_riparatore = ddt.data_documento
        update_fields.append("data_riparatore")

    pratica.save(update_fields=update_fields)


def _clear_pratica_ddt(pratica, user=None):
    pratica.ddt_numero = ""
    pratica.ddt_data = None
    pratica.updated_by = user
    pratica.save(update_fields=["ddt_numero", "ddt_data", "updated_by", "updated_at"])


def _set_pratica_ddt(pratica, ddt, user=None):
    _apply_pratica_on_ddt_assign(pratica, ddt, user=user)


@transaction.atomic
def update_ddt(
    *,
    ddt,
    user=None,
    data_documento=None,
    causale=None,
    aspetto_beni=None,
    trasporto_a_cura=None,
    vettore=None,
    peso_lordo_kg=None,
    colli=None,
    data_inizio_trasporto=None,
    ora_inizio_trasporto=None,
    destinazione_merce=None,
    agente=None,
    note=None,
    refresh_destinatario=False,
):
    if not ddt or not ddt.is_active:
        raise ValueError("DDT non trovato.")

    # Le riparazioni del DDT restano quelle di creazione: non si aggiungono né rimuovono.
    pratiche = [
        r.pratica
        for r in ddt.righe.filter(is_active=True).select_related("pratica").order_by("ordine", "id")
        if r.pratica_id
    ]
    if not pratiche:
        raise ValueError("Il DDT non ha buste associate.")

    centro = ddt.centro_assistenza

    if data_documento is not None:
        ddt.data_documento = data_documento
    if causale is not None:
        ddt.causale = (causale or DDT_CAUSALE_DEFAULT).strip() or DDT_CAUSALE_DEFAULT
    if aspetto_beni is not None:
        ddt.aspetto_beni = (aspetto_beni or DDT_ASPETTO_DEFAULT).strip() or DDT_ASPETTO_DEFAULT
    if trasporto_a_cura is not None:
        ddt.trasporto_a_cura = (
            (trasporto_a_cura or DDT_TRASPORTO_DEFAULT).strip() or DDT_TRASPORTO_DEFAULT
        )
    if vettore is not None:
        ddt.vettore = (vettore or DDT_VETTORE_DEFAULT).strip() or DDT_VETTORE_DEFAULT
    if peso_lordo_kg is not None:
        ddt.peso_lordo_kg = peso_lordo_kg
    if colli is not None:
        ddt.colli = colli
    if data_inizio_trasporto is not None:
        ddt.data_inizio_trasporto = data_inizio_trasporto
    if ora_inizio_trasporto is not None:
        ddt.ora_inizio_trasporto = ora_inizio_trasporto
    if destinazione_merce is not None:
        ddt.destinazione_merce = (destinazione_merce or "").strip()
    if agente is not None:
        ddt.agente = (agente or "").strip()
    if note is not None:
        ddt.note = (note or "").strip()

    if refresh_destinatario:
        for key, value in snapshot_destinatario_from_centro(centro).items():
            setattr(ddt, key, value)

    ddt.updated_by = user
    ddt.save()

    for pratica in pratiche:
        _set_pratica_ddt(pratica, ddt, user=user)

    return ddt


def _sync_ddt_colli(ddt, user=None):
    count = ddt.righe.filter(is_active=True).count()
    ddt.colli = max(1, count) if count else 0
    ddt.updated_by = user
    ddt.save(update_fields=["colli", "updated_by", "updated_at"])


def _renumber_ddt_righe(ddt, user=None):
    for index, riga in enumerate(
        ddt.righe.filter(is_active=True).order_by("ordine", "id"),
        start=1,
    ):
        if riga.ordine != index:
            riga.ordine = index
            riga.updated_by = user
            riga.save(update_fields=["ordine", "updated_by", "updated_at"])


@transaction.atomic
def add_ddt_riga(*, ddt, pratica, user=None):
    if not ddt or not ddt.is_active:
        raise ValueError("DDT non trovato.")
    if not pratica or not pratica.is_active:
        raise ValueError("Riparazione non valida.")
    if pratica.stato in STATI_BUSTE_CHIUSE:
        raise ValueError(f"La riparazione {pratica.codice} non è una busta aperta.")
    existing_numero = (pratica.ddt_numero or "").strip()
    if existing_numero and existing_numero != ddt.numero_display:
        raise ValueError(f"La riparazione {pratica.codice} ha già il DDT {existing_numero}.")
    if ddt.righe.filter(is_active=True, pratica_id=pratica.pk).exists():
        raise ValueError(f"La riparazione {pratica.codice} è già presente in questo DDT.")

    max_ordine = (
        ddt.righe.filter(is_active=True).aggregate(Max("ordine"))["ordine__max"] or 0
    )
    DdtRiga.objects.create(
        ddt=ddt,
        pratica=pratica,
        ordine=max_ordine + 1,
        articolo=format_busta_articolo(pratica),
        descrizione=format_busta_descrizione(pratica),
        unita_misura="NR",
        quantita=Decimal("1.00"),
        created_by=user,
        updated_by=user,
    )
    _set_pratica_ddt(pratica, ddt, user=user)
    _sync_ddt_colli(ddt, user=user)
    return ddt


@transaction.atomic
def remove_ddt_riga(*, ddt, riga, user=None):
    if not ddt or not ddt.is_active:
        raise ValueError("DDT non trovato.")
    if not riga or not riga.is_active or riga.ddt_id != ddt.pk:
        raise ValueError("Riga non trovata.")
    if ddt.righe.filter(is_active=True).count() <= 1:
        raise ValueError("Non puoi eliminare l'ultima riga del DDT.")

    pratica = riga.pratica
    riga.soft_delete(user=user)
    if pratica is not None:
        _clear_pratica_ddt(pratica, user=user)
    _renumber_ddt_righe(ddt, user=user)
    _sync_ddt_colli(ddt, user=user)
    return ddt


@transaction.atomic
def delete_ddt(*, ddt, user=None):
    if not ddt or not ddt.is_active:
        raise ValueError("DDT non trovato.")

    for riga in ddt.righe.filter(is_active=True).select_related("pratica"):
        if riga.pratica_id:
            _clear_pratica_ddt(riga.pratica, user=user)
        riga.soft_delete(user=user)

    ddt.soft_delete(user=user)
    return ddt
