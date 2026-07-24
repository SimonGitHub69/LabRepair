import csv
import io
from datetime import datetime

from django.db import transaction

from apps.anagrafiche.models import Anagrafica, Indirizzo


DOCUMENTO_TIPO_MAP = {
    "CI": Anagrafica.TipoDocumento.CARTA_IDENTITA,
    "PAT": Anagrafica.TipoDocumento.PATENTE,
    "PP": Anagrafica.TipoDocumento.PASSAPORTO,
}


def clean(value):
    return (value or "").strip()


def clean_provincia(value):
    value = clean(value).upper()
    return value[:2]


def parse_date(value):
    value = clean(value)
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def map_documento_tipo(value):
    key = clean(value).upper()
    return DOCUMENTO_TIPO_MAP.get(key, clean(value))


def build_ragione_sociale(cognome, nome, ragione_sociale):
    full_name = f"{cognome} {nome}".strip()
    return full_name or ragione_sociale or cognome or nome


def _row_document_dates(row):
    return {
        "documento_data_rilascio": parse_date(row.get("AN_DATADOCUMENTO")),
        "documento_data_scadenza": parse_date(row.get("AN_SCADENZADOCUMENTO")),
        "data_nascita": parse_date(row.get("AN_DATANASCITA")),
        "documento_rilasciato_da": clean(row.get("AN_RILASCIATODA")),
        "documento_tipo": map_documento_tipo(row.get("AN_IDTIPODOCUMENTO")),
        "documento_numero": clean(row.get("AN_DOCUMENTO")),
    }


def _would_fill_empty_fields(anagrafica, row):
    values = _row_document_dates(row)
    for field, value in values.items():
        if not value:
            continue
        current = getattr(anagrafica, field, None)
        if current in (None, ""):
            return True
    return False


def _fill_empty_document_dates(anagrafica, row):
    """Compila date/documento solo se ancora vuoti sull'anagrafica esistente."""
    values = _row_document_dates(row)
    update_fields = []
    for field, value in values.items():
        if not value:
            continue
        current = getattr(anagrafica, field, None)
        if current in (None, ""):
            setattr(anagrafica, field, value)
            update_fields.append(field)
    if update_fields:
        anagrafica.save(update_fields=update_fields)
        return True
    return False


def _empty_stats():
    return {
        "created": 0,
        "updated": 0,
        "skipped_existing": 0,
        "skipped_duplicate_csv": 0,
        "skipped_invalid": 0,
        "total_rows": 0,
    }


def _read_csv_rows(file_obj):
    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = raw
        handle = io.StringIO(text)
    else:
        handle = open(file_obj, encoding="utf-8-sig", newline="")

    try:
        return list(csv.DictReader(handle, delimiter=";"))
    finally:
        if handle is not file_obj and hasattr(handle, "close"):
            if not isinstance(handle, io.StringIO):
                handle.close()


def import_clienti_csv(file_obj, *, dry_run=False, update_existing=False):
    """
    Importa clienti da CSV (tracciato Pistoia, separatore ;).
    file_obj: percorso stringa oppure file-like (upload).
    """
    rows = _read_csv_rows(file_obj)
    if not rows:
        raise ValueError("Il file CSV non contiene righe da importare.")

    existing_by_cf = {}
    for anagrafica in Anagrafica.objects.filter(
        tipo=Anagrafica.Tipo.CLIENTE,
        is_active=True,
    ).exclude(codice_fiscale=""):
        existing_by_cf[anagrafica.codice_fiscale.upper()] = anagrafica

    seen_cf = set()
    stats = _empty_stats()
    stats["total_rows"] = len(rows)

    @transaction.atomic
    def run_import():
        for row in rows:
            cognome = clean(row.get("AN_COGNOME"))
            nome = clean(row.get("AN_NOME"))
            ragione_sociale = clean(row.get("AN_RAGIONESOCIALE"))
            codice_fiscale = clean(row.get("AN_CODICEFISCALE")).upper()

            if not (cognome or nome or ragione_sociale):
                stats["skipped_invalid"] += 1
                continue

            if codice_fiscale:
                if codice_fiscale in seen_cf:
                    stats["skipped_duplicate_csv"] += 1
                    continue
                seen_cf.add(codice_fiscale)

                existing = existing_by_cf.get(codice_fiscale)
                if existing and not update_existing:
                    # Completa solo i campi documento/date ancora vuoti, senza sovrascrivere
                    # i dati già presenti (utile su re-import).
                    if dry_run:
                        if _would_fill_empty_fields(existing, row):
                            stats["updated"] += 1
                        else:
                            stats["skipped_existing"] += 1
                    else:
                        filled = _fill_empty_document_dates(existing, row)
                        if filled:
                            stats["updated"] += 1
                        else:
                            stats["skipped_existing"] += 1
                    continue
            else:
                existing = None

            anagrafica_data = {
                "tipo": Anagrafica.Tipo.CLIENTE,
                "cognome": cognome,
                "nome": nome,
                "ragione_sociale": build_ragione_sociale(cognome, nome, ragione_sociale),
                "sesso": clean(row.get("AN_SESSO")).upper()[:1],
                "data_nascita": parse_date(row.get("AN_DATANASCITA")),
                "provincia_nascita": clean_provincia(row.get("AN_PROVINCIANASCITA")),
                "luogo_nascita": clean(row.get("AN_LUOGONASCITA")),
                "documento_tipo": map_documento_tipo(row.get("AN_IDTIPODOCUMENTO")),
                "documento_numero": clean(row.get("AN_DOCUMENTO")),
                "documento_data_rilascio": parse_date(row.get("AN_DATADOCUMENTO")),
                "documento_data_scadenza": parse_date(row.get("AN_SCADENZADOCUMENTO")),
                "documento_rilasciato_da": clean(row.get("AN_RILASCIATODA")),
                "email": clean(row.get("AN_EMAIL")),
                "telefono": clean(row.get("AN_TELEFONO")),
                "cellulare": clean(row.get("AN_CELLULARE")),
                "codice_fiscale": codice_fiscale,
                "partita_iva": clean(row.get("AN_PARTITAIVA")),
                "note": clean(row.get("AN_NOTE")),
                "is_active": True,
            }

            indirizzo = clean(row.get("AN_INDIRIZZO"))
            cap = clean(row.get("AN_CAP"))
            comune = clean(row.get("AN_COMUNE"))
            provincia = clean_provincia(row.get("AN_PROVINCIA"))

            if dry_run:
                if existing and update_existing:
                    stats["updated"] += 1
                elif existing:
                    stats["skipped_existing"] += 1
                else:
                    stats["created"] += 1
                continue

            if existing and update_existing:
                for field, value in anagrafica_data.items():
                    setattr(existing, field, value)
                existing.save()
                anagrafica = existing
                stats["updated"] += 1
            else:
                anagrafica = Anagrafica.objects.create(**anagrafica_data)
                if codice_fiscale:
                    existing_by_cf[codice_fiscale] = anagrafica
                stats["created"] += 1

            if indirizzo:
                indirizzo_obj = (
                    anagrafica.indirizzi.filter(
                        tipo=Indirizzo.TipoIndirizzo.RESIDENZA,
                        is_active=True,
                    )
                    .order_by("-principale", "pk")
                    .first()
                )
                indirizzo_data = {
                    "indirizzo": indirizzo,
                    "cap": cap,
                    "comune": comune,
                    "provincia": provincia,
                    "principale": True,
                    "is_active": True,
                }
                if indirizzo_obj:
                    for field, value in indirizzo_data.items():
                        setattr(indirizzo_obj, field, value)
                    indirizzo_obj.save()
                else:
                    Indirizzo.objects.create(
                        anagrafica=anagrafica,
                        tipo=Indirizzo.TipoIndirizzo.RESIDENZA,
                        **indirizzo_data,
                    )

    run_import()
    return stats


def format_import_stats(stats, *, dry_run=False):
    mode = "Simulazione" if dry_run else "Importazione"
    return (
        f"{mode} completata: {stats['created']} creati, "
        f"{stats['updated']} aggiornati, "
        f"{stats['skipped_existing']} già presenti, "
        f"{stats['skipped_duplicate_csv']} duplicati nel CSV, "
        f"{stats['skipped_invalid']} righe non valide "
        f"(su {stats['total_rows']} righe)."
    )
