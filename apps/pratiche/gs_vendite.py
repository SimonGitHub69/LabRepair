"""Lettura pagamenti da Database Cassa (vista GS_VENDITE_DETTAGLIO).

Cerca ID_ARTICOLO = codice riparazione (con e senza trattino),
legge DATA_SCONTRINO, NUM_SCONTRINO e TOTALE_RIGA_IVATO_D,
aggiorna Prezzo pagato / N. scontrino e imposta stato Evasa se non lo e' gia'.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.core.mssql import get_mssql_config, open_mssql_cassa_connection
from apps.core.negozi import NEGOZIO_FILTER_ALL, normalize_negozio_code
from apps.pratiche.gs_articoli import format_prz_ean
from apps.pratiche.models import Pratica

logger = logging.getLogger(__name__)

# Stati esclusi dalla sync automatica (non devono diventare Evasa da cassa).
STATI_ESCLUSI = {
    Pratica.Stato.ANNULLATA,
    Pratica.Stato.ARCHIVIATA,
}

# Candidati in elenco: qualsiasi stato ancora "aperto" (non solo In consegna).
STATI_PENDING_DEFAULT = {
    Pratica.Stato.ACCETTAZIONE,
    Pratica.Stato.RIPARATORE,
    Pratica.Stato.IN_CONSEGNA,
    Pratica.Stato.NON_RITIRATA,
}


@dataclass
class GsVenditaSyncResult:
    ok: bool
    message: str
    found: bool = False
    updated: bool = False


@dataclass
class GsVenditaRow:
    id_articolo: str
    data_scontrino: date | None
    numero_scontrino: str
    totale: Decimal


def _id_articolo_variants(codice: str) -> list[str]:
    raw = (codice or "").strip()
    if not raw:
        return []
    variants = [raw]
    no_hyphen = format_prz_ean(raw) or raw.replace("-", "").replace(" ", "")
    if no_hyphen and no_hyphen not in variants:
        variants.append(no_hyphen)
    return variants


def _to_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_numero_scontrino(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        value = int(value)
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text[:30]


def _fetch_vendite_map(cursor, articoli: list[str]) -> dict[str, GsVenditaRow]:
    """Ritorna mappa id_articolo(upper) -> riga piu' recente."""
    result: dict[str, GsVenditaRow] = {}
    unique = []
    seen = set()
    for art in articoli:
        key = (art or "").strip()
        if not key:
            continue
        upper = key.upper()
        if upper in seen:
            continue
        seen.add(upper)
        unique.append(key)

    if not unique:
        return result

    chunk_size = 80
    for start in range(0, len(unique), chunk_size):
        chunk = unique[start : start + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        sql = f"""
            SELECT ID_ARTICOLO, DATA_SCONTRINO, TOTALE_RIGA_IVATO_D, NUM_SCONTRINO
            FROM GS_VENDITE_DETTAGLIO
            WHERE ID_ARTICOLO IN ({placeholders})
            ORDER BY DATA_SCONTRINO DESC
        """
        cursor.execute(sql, chunk)
        for row in cursor.fetchall():
            id_art = str(row[0] or "").strip()
            if not id_art:
                continue
            key = id_art.upper()
            if key in result:
                continue
            totale = _to_decimal(row[2])
            if totale is None:
                continue
            result[key] = GsVenditaRow(
                id_articolo=id_art,
                data_scontrino=_to_date(row[1]),
                totale=totale,
                numero_scontrino=_to_numero_scontrino(row[3]),
            )
    return result


def _lookup_row(vendite: dict[str, GsVenditaRow], codice: str) -> GsVenditaRow | None:
    for variant in _id_articolo_variants(codice):
        row = vendite.get(variant.upper())
        if row:
            return row
    return None


def apply_vendita_to_pratica(pratica: Pratica, row: GsVenditaRow, *, save: bool = True) -> bool:
    """Applica importo, n. scontrino e (se serve) stato Evasa. Ritorna True se ha modificato."""
    changed = False

    if pratica.prezzo_pagato != row.totale:
        pratica.prezzo_pagato = row.totale
        changed = True

    if row.data_scontrino and pratica.data_vendita != row.data_scontrino:
        pratica.data_vendita = row.data_scontrino
        changed = True

    num = (row.numero_scontrino or "").strip()
    if num and (pratica.numero_scontrino or "").strip() != num:
        pratica.numero_scontrino = num
        changed = True

    if pratica.stato != Pratica.Stato.EVASA:
        pratica.stato = Pratica.Stato.EVASA
        changed = True

    if changed and save:
        pratica.save()
    return changed


def sync_pagamento_da_cassa(pratica: Pratica, *, force: bool = False) -> GsVenditaSyncResult:
    """Sincronizza una singola riparazione dal Database Cassa."""
    config = get_mssql_config()
    if not config.attiva:
        return GsVenditaSyncResult(ok=True, message="Collegamento MS-SQL disattivato.")

    if not config.is_cassa_configured:
        return GsVenditaSyncResult(
            ok=False,
            message="Database Cassa non configurato (nome database cassa mancante).",
        )

    codice = (pratica.codice or "").strip()
    if not codice:
        return GsVenditaSyncResult(ok=False, message="Codice riparazione mancante.")

    if not force and pratica.stato in STATI_ESCLUSI:
        return GsVenditaSyncResult(
            ok=True,
            message=f"Riparazione {codice} esclusa (stato {pratica.get_stato_display()}).",
        )

    variants = _id_articolo_variants(codice)
    try:
        with open_mssql_cassa_connection(config, timeout=2) as connection:
            cursor = connection.cursor()
            vendite = _fetch_vendite_map(cursor, variants)
    except Exception as exc:
        logger.warning("Lettura GS_VENDITE_DETTAGLIO fallita per %s: %s", codice, exc)
        return GsVenditaSyncResult(
            ok=False,
            message=f"Lettura Database Cassa non riuscita: {exc}",
        )

    row = _lookup_row(vendite, codice)
    if not row:
        return GsVenditaSyncResult(
            ok=True,
            found=False,
            message=f"Nessuno scontrino in cassa per {codice}.",
        )

    updated = apply_vendita_to_pratica(pratica, row)
    if updated:
        parts = [f"Pagamento cassa per {codice}: {row.totale} €"]
        if row.numero_scontrino:
            parts.append(f"scontrino {row.numero_scontrino}")
        if row.data_scontrino:
            parts.append(f"del {row.data_scontrino.strftime('%d/%m/%Y')}")
        parts.append("stato Evasa.")
        return GsVenditaSyncResult(
            ok=True,
            found=True,
            updated=True,
            message=" · ".join(parts),
        )
    return GsVenditaSyncResult(
        ok=True,
        found=True,
        updated=False,
        message=f"Riparazione {codice} gia' allineata allo scontrino cassa.",
    )


def sync_pagamenti_cassa_pending(
    *,
    negozio: str | None = None,
    stati: set[str] | None = None,
    limit: int = 200,
    dry_run: bool = False,
) -> dict:
    """
    Sincronizza le riparazioni candidate (default: In consegna).
    Ritorna contatori: checked, found, updated, errors.
    """
    config = get_mssql_config()
    stats = {"checked": 0, "found": 0, "updated": 0, "errors": 0, "skipped": False}

    if not config.attiva:
        stats["skipped"] = True
        return stats
    if not config.is_cassa_configured:
        stats["skipped"] = True
        return stats

    stati = stati or set(STATI_PENDING_DEFAULT)
    qs = (
        Pratica.objects.filter(is_active=True, stato__in=stati)
        .exclude(codice="")
        .order_by("-data_apertura", "-id")
    )
    negozio_code = (
        normalize_negozio_code(negozio)
        if negozio and negozio != NEGOZIO_FILTER_ALL
        else ""
    )
    if negozio_code:
        qs = qs.filter(negozio=negozio_code)

    pratiche = list(qs[: max(1, int(limit or 200))])
    stats["checked"] = len(pratiche)
    if not pratiche:
        return stats

    articoli: list[str] = []
    for pratica in pratiche:
        articoli.extend(_id_articolo_variants(pratica.codice))

    try:
        with open_mssql_cassa_connection(config, timeout=3) as connection:
            cursor = connection.cursor()
            vendite = _fetch_vendite_map(cursor, articoli)
    except Exception as exc:
        logger.warning("Sync batch GS_VENDITE_DETTAGLIO fallita: %s", exc)
        stats["errors"] = 1
        return stats

    for pratica in pratiche:
        row = _lookup_row(vendite, pratica.codice)
        if not row:
            continue
        stats["found"] += 1
        if dry_run:
            continue
        try:
            if apply_vendita_to_pratica(pratica, row):
                stats["updated"] += 1
        except Exception as exc:
            stats["errors"] += 1
            logger.exception(
                "Aggiornamento pratica %s da cassa fallito: %s", pratica.codice, exc
            )

    return stats
