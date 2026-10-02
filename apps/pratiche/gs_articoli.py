"""Sincronizzazione riparazioni verso TB_PREZZICASSE (casse / gestionale SQL).

Allineato alla procedura 4D: DELETE per EAN + INSERT su TB_PREZZICASSE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from apps.core.mssql import get_mssql_config, open_mssql_connection
from apps.core.programma import get_gs_barcode_min

GS_BARCODE_MAX_EXCLUSIVE = 90000000

# Lunghezze colonne TB_PREZZICASSE (INFORMATION_SCHEMA).
PRZ_PVN_LEN = 2
PRZ_EAN_LEN = 14
PRZ_COR_LEN = 5
PRZ_CODART_LEN = 13
PRZ_FOR_LEN = 15
PRZ_DESCR_LEN = 50
PRZ_REP_LEN = 5
PRZ_LIN_LEN = 5
PRZ_CAT_LEN = 5
PRZ_CODARTFORN_LEN = 50
PRZ_UM_LEN = 5
PRZ_STATO_ARTICOLO_LEN = 50
PRZ_LOTTO_LEN = 5


@dataclass
class GsArticoloSyncResult:
    ok: bool
    message: str
    barcode: str | None = None
    created: bool = False


def _clip(value, max_len: int) -> str:
    return str(value or "").strip()[:max_len]


def format_gs_utente(user):
    username = getattr(user, "username", "") or "sistema"
    return f"LabRepair-{username}"


def format_gs_descrizione(pratica):
    parts = []
    if pratica.tipo_oggetto_id:
        parts.append(pratica.tipo_oggetto.denominazione.strip())
    if pratica.descrizione:
        parts.append(pratica.descrizione.strip())
    if not parts and pratica.titolo:
        parts.append(pratica.titolo.strip())
    text = " - ".join(part for part in parts if part)
    return _clip(text or "RIPARAZIONE", PRZ_DESCR_LEN)


def format_gs_prezzo(pratica):
    """PRZ_PREZZO = Prezzo al Pubblico della riparazione."""
    return Decimal(pratica.prezzo_al or 0).quantize(Decimal("0.01"))


def _sql_datetime(value) -> datetime:
    if value is None:
        return timezone.localtime().replace(tzinfo=None)
    if timezone.is_aware(value):
        return timezone.localtime(value).replace(tzinfo=None)
    return value


def is_valid_repair_barcode(barcode):
    if barcode is None:
        return False
    try:
        value = int(barcode)
    except (TypeError, ValueError):
        return False
    barcode_min = get_gs_barcode_min()
    return barcode_min <= value < GS_BARCODE_MAX_EXCLUSIVE


def _ean_str(barcode) -> str:
    return _clip(str(int(barcode)), PRZ_EAN_LEN)


def format_prz_ean(codice: str) -> str:
    """PRZ_EAN = codice riparazione senza trattini (P26-0026 → P260026)."""
    raw = str(codice or "").strip().replace("-", "").replace(" ", "")
    return _clip(raw, PRZ_EAN_LEN)


def exists_by_codart(cursor, codart):
    cursor.execute("SELECT 1 FROM TB_PREZZICASSE WHERE PRZ_CODART = ?", codart)
    return cursor.fetchone() is not None


def resolve_iva_cassa(cursor, config):
    """Usa la config LabRepair (default 10 / 22), altrimenti l'IVA piu' frequente su TB_PREZZICASSE."""
    if config.iva_id_cassa:
        return (
            int(config.iva_id_cassa),
            Decimal(config.iva_aliquota_cassa or 22).quantize(Decimal("0.01")),
        )

    # Default operativo casse (configurabile in Parametri sistema).
    return 10, Decimal("22.00")


def build_prezzi_casse_payload(pratica, user, ean, config, *, iva_id=None, iva_aliquota=None):
    now = timezone.localtime()
    created = pratica.created_at or now
    updated = pratica.updated_at or now
    return {
        "PRZ_PVN_CODICE": _clip(config.prz_pvn_codice or "TN", PRZ_PVN_LEN) or "TN",
        "PRZ_EAN": _clip(ean, PRZ_EAN_LEN),
        "PRZ_COR_CODICE": _clip("MAN", PRZ_COR_LEN),
        "PRZ_MOLTIPLICATORE_EAN": 1,
        "PRZ_CONFEZIONE": 1,
        "PRZ_CODART": _clip(pratica.codice, PRZ_CODART_LEN),
        "PRZ_FOR_CODICE": _clip("", PRZ_FOR_LEN),
        "PRZ_DESCR": format_gs_descrizione(pratica),
        "PRZ_REP_CODICE": _clip("", PRZ_REP_LEN),
        "PRZ_LIN_CODICE": _clip("", PRZ_LIN_LEN),
        "PRZ_CAT_CODICE": _clip("", PRZ_CAT_LEN),
        "PRZ_PREZZOACQ": Decimal("0.00"),
        "PRZ_PREZZO": format_gs_prezzo(pratica),
        "PRZ_SC1": Decimal("0.00"),
        "PRZ_INVIO_A_FORNITORE": 0,
        "PRZ_CODARTFORN": _clip("", PRZ_CODARTFORN_LEN),
        "PRZ_UM": _clip("", PRZ_UM_LEN),
        "PRZ_STATO_ARTICOLO": _clip("", PRZ_STATO_ARTICOLO_LEN),
        "PRZ_NOTE": format_gs_utente(user),
        "PRZ_FRAZIONABILE": 0,
        "PRZ_VENDITAAPESO": 0,
        "PRZ_NONSCONTABILE": 0,
        "PRZ_PETSHOP": 0,
        "PRZ_LOTTO_RIORDINO": _clip("", PRZ_LOTTO_LEN),
        "PRZ_IVA_ID": int(iva_id if iva_id is not None else (config.iva_id_cassa or 10)),
        "PRZ_IVA_ALIQUOTA": Decimal(
            iva_aliquota if iva_aliquota is not None else (config.iva_aliquota_cassa or 22)
        ).quantize(Decimal("0.01")),
        "PRZ_STATO": "K",
        "PRZ_DATAINSERIMENTO": _sql_datetime(created),
        "PRZ_DATAAGGIORNAMENTO": _sql_datetime(updated),
        "PRZ_EAN_ATTIVO": 1,
        "PRZ_ANNULLATO": 0,
        "PRZ_TIPO_VENDITA": "N",
        "PRZ_DATAUPDATESQL": _sql_datetime(now),
    }


def delete_prezzi_casse(cursor, *, ean: str, codart: str, legacy_ean: str | None = None):
    if legacy_ean and legacy_ean != ean:
        cursor.execute(
            """
            DELETE FROM TB_PREZZICASSE
            WHERE PRZ_EAN = ? OR PRZ_EAN = ? OR PRZ_CODART = ?
            """,
            ean,
            legacy_ean,
            codart,
        )
        return
    cursor.execute(
        """
        DELETE FROM TB_PREZZICASSE
        WHERE PRZ_EAN = ? OR PRZ_CODART = ?
        """,
        ean,
        codart,
    )


def insert_prezzi_casse(cursor, payload):
    cursor.execute(
        """
        INSERT INTO TB_PREZZICASSE (
            PRZ_PVN_CODICE, PRZ_EAN, PRZ_COR_CODICE, PRZ_MOLTIPLICATORE_EAN, PRZ_CONFEZIONE,
            PRZ_CODART, PRZ_FOR_CODICE, PRZ_DESCR, PRZ_REP_CODICE, PRZ_LIN_CODICE,
            PRZ_CAT_CODICE, PRZ_PREZZOACQ, PRZ_PREZZO, PRZ_SC1, PRZ_INVIO_A_FORNITORE,
            PRZ_CODARTFORN, PRZ_UM, PRZ_STATO_ARTICOLO, PRZ_NOTE, PRZ_FRAZIONABILE,
            PRZ_VENDITAAPESO, PRZ_NONSCONTABILE, PRZ_PETSHOP, PRZ_LOTTO_RIORDINO,
            PRZ_IVA_ID, PRZ_IVA_ALIQUOTA, PRZ_STATO, PRZ_DATAINSERIMENTO, PRZ_DATAAGGIORNAMENTO,
            PRZ_EAN_ATTIVO, PRZ_ANNULLATO, PRZ_TIPO_VENDITA, PRZ_DATAUPDATESQL
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?
        )
        """,
        payload["PRZ_PVN_CODICE"],
        payload["PRZ_EAN"],
        payload["PRZ_COR_CODICE"],
        payload["PRZ_MOLTIPLICATORE_EAN"],
        payload["PRZ_CONFEZIONE"],
        payload["PRZ_CODART"],
        payload["PRZ_FOR_CODICE"],
        payload["PRZ_DESCR"],
        payload["PRZ_REP_CODICE"],
        payload["PRZ_LIN_CODICE"],
        payload["PRZ_CAT_CODICE"],
        payload["PRZ_PREZZOACQ"],
        payload["PRZ_PREZZO"],
        payload["PRZ_SC1"],
        payload["PRZ_INVIO_A_FORNITORE"],
        payload["PRZ_CODARTFORN"],
        payload["PRZ_UM"],
        payload["PRZ_STATO_ARTICOLO"],
        payload["PRZ_NOTE"],
        payload["PRZ_FRAZIONABILE"],
        payload["PRZ_VENDITAAPESO"],
        payload["PRZ_NONSCONTABILE"],
        payload["PRZ_PETSHOP"],
        payload["PRZ_LOTTO_RIORDINO"],
        payload["PRZ_IVA_ID"],
        payload["PRZ_IVA_ALIQUOTA"],
        payload["PRZ_STATO"],
        payload["PRZ_DATAINSERIMENTO"],
        payload["PRZ_DATAAGGIORNAMENTO"],
        payload["PRZ_EAN_ATTIVO"],
        payload["PRZ_ANNULLATO"],
        payload["PRZ_TIPO_VENDITA"],
        payload["PRZ_DATAUPDATESQL"],
    )


def sync_pratica_to_gs_articoli(pratica, user):
    """Sincronizza la riparazione su TB_PREZZICASSE (DELETE EAN + INSERT)."""
    config = get_mssql_config()
    if not config.attiva:
        return GsArticoloSyncResult(
            ok=True,
            message="Collegamento MS-SQL disattivato.",
        )

    if not config.is_configured:
        return GsArticoloSyncResult(
            ok=False,
            message="Collegamento MS-SQL attivo ma incompleto.",
        )

    codart = _clip(pratica.codice, PRZ_CODART_LEN)
    if not codart:
        return GsArticoloSyncResult(
            ok=False,
            message="Codice riparazione mancante, impossibile sincronizzare TB_PREZZICASSE.",
        )

    try:
        with open_mssql_connection(config, timeout=2) as connection:
            cursor = connection.cursor()
            iva_id, iva_aliquota = resolve_iva_cassa(cursor, config)
            created = not exists_by_codart(cursor, codart)
            ean = format_prz_ean(codart)
            if not ean:
                return GsArticoloSyncResult(
                    ok=False,
                    message="Codice riparazione non valido per PRZ_EAN.",
                )
            legacy_ean = None
            if is_valid_repair_barcode(pratica.gs_barcode):
                legacy_ean = _ean_str(pratica.gs_barcode)
            payload = build_prezzi_casse_payload(
                pratica,
                user,
                ean,
                config,
                iva_id=iva_id,
                iva_aliquota=iva_aliquota,
            )
            delete_prezzi_casse(
                cursor,
                ean=payload["PRZ_EAN"],
                codart=codart,
                legacy_ean=legacy_ean,
            )
            insert_prezzi_casse(cursor, payload)
            connection.commit()

        azione = "creato" if created else "aggiornato"
        return GsArticoloSyncResult(
            ok=True,
            message=f"Prezzo cassa {azione} ({codart}, EAN {ean}, IVA {iva_id}).",
            barcode=ean,
            created=created,
        )
    except Exception as exc:
        return GsArticoloSyncResult(
            ok=False,
            message=f"Sincronizzazione TB_PREZZICASSE non riuscita: {exc}",
        )
