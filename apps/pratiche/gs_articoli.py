from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.core.mssql import get_mssql_config, open_mssql_connection
from apps.core.programma import get_gs_barcode_min
from apps.pratiche.models import Pratica

GS_BARCODE_MAX_EXCLUSIVE = 90000000


@dataclass
class GsArticoloSyncResult:
    ok: bool
    message: str
    barcode: int | None = None
    created: bool = False


def format_gs_utente(user):
    username = getattr(user, "username", "") or "sistema"
    return f"LabRepair-{username}"[:80]


def format_gs_cliente(pratica):
    if pratica.cliente_id and pratica.cliente.codice_gestionale:
        return pratica.cliente.codice_gestionale.strip().ljust(7)[:7]
    return "       "


def format_gs_descrizione(pratica):
    parts = []
    if pratica.tipo_oggetto_id:
        parts.append(pratica.tipo_oggetto.denominazione.strip())
    if pratica.descrizione:
        parts.append(pratica.descrizione.strip())
    if not parts and pratica.titolo:
        parts.append(pratica.titolo.strip())
    text = " - ".join(part for part in parts if part)
    return (text or "RIPARAZIONE")[:80]


def format_gs_stato(pratica):
    # Usato solo in INSERT; in UPDATE lo STATO SQL non viene toccato.
    return "RIP"


def format_gs_prezzo(pratica):
    """PREZZOLISTINO su GS_ARTICOLI = Prezzo al Pubblico della riparazione."""
    return Decimal(pratica.prezzo_al or 0).quantize(Decimal("0.01"))


def format_gs_peso(pratica):
    return Decimal(pratica.peso_grammi or 0).quantize(Decimal("0.001"))


TIPO_MATERIALE_GS_MAP = {
    Pratica.TipoMetallo.ORO: "ORO",
    Pratica.TipoMetallo.ARGENTO: "ARGENT",
    Pratica.TipoMetallo.PLATINO: "PLATIN",
}


def format_gs_tipo_materiale(pratica):
    code = TIPO_MATERIALE_GS_MAP.get(pratica.tipo_metallo, "")
    return code.ljust(6)[:6] if code else " " * 6


def build_gs_articolo_payload(pratica, user, barcode):
    now = timezone.localtime()
    return {
        "BARCODE": barcode,
        "CODART": (pratica.codice or "")[:20],
        "DESCRIZIONE": format_gs_descrizione(pratica),
        "CODCAT1": "",
        "CODCAT2": "",
        "CODCAT3": " " * 15,
        "CODMARCHIO": " " * 4,
        "TIPOMATERIALE": format_gs_tipo_materiale(pratica),
        "PESO": format_gs_peso(pratica),
        "PREZZOLISTINO": format_gs_prezzo(pratica),
        "ARTICOLOAQTA": 0,
        "STATO": format_gs_stato(pratica),
        "CODNEGOZIO": (pratica.negozio or "")[:2],
        "CODCLIENTE": format_gs_cliente(pratica),
        "NUMFILIALE": 0,
        "NUMDOC": "",
        "DATADOC": None,
        "TIPODOC": "",
        "DUPLICATO": None,
        "utentemodifica": format_gs_utente(user),
        "datamodifica": now.replace(tzinfo=None),
    }


def is_valid_repair_barcode(barcode):
    if barcode is None:
        return False
    value = int(barcode)
    barcode_min = get_gs_barcode_min()
    return barcode_min <= value < GS_BARCODE_MAX_EXCLUSIVE


def allocate_gs_barcode(cursor):
    barcode_min = get_gs_barcode_min()
    cursor.execute(
        """
        SELECT MAX(BARCODE)
        FROM GS_ARTICOLI WITH (UPDLOCK, HOLDLOCK)
        WHERE BARCODE >= ? AND BARCODE < ?
        """,
        barcode_min,
        GS_BARCODE_MAX_EXCLUSIVE,
    )
    current = cursor.fetchone()[0]
    if current is None:
        return barcode_min
    return max(barcode_min, int(current) + 1)


def get_gs_barcode_by_codart(cursor, codart):
    cursor.execute("SELECT BARCODE FROM GS_ARTICOLI WHERE CODART = ?", codart)
    row = cursor.fetchone()
    return int(row[0]) if row else None


def gs_articolo_exists_by_codart(cursor, codart):
    cursor.execute("SELECT 1 FROM GS_ARTICOLI WHERE CODART = ?", codart)
    return cursor.fetchone() is not None


def is_barcode_available(cursor, barcode):
    cursor.execute("SELECT 1 FROM GS_ARTICOLI WHERE BARCODE = ?", barcode)
    return cursor.fetchone() is None


def resolve_gs_barcode(cursor, pratica, codart, *, for_insert=False):
    existing = get_gs_barcode_by_codart(cursor, codart)
    if is_valid_repair_barcode(existing):
        return existing

    if for_insert and is_valid_repair_barcode(pratica.gs_barcode):
        cached_barcode = int(pratica.gs_barcode)
        if is_barcode_available(cursor, cached_barcode):
            return cached_barcode

    return allocate_gs_barcode(cursor)


def insert_gs_articolo(cursor, payload):
    cursor.execute(
        """
        INSERT INTO GS_ARTICOLI (
            BARCODE, CODART, DESCRIZIONE, CODCAT1, CODCAT2, CODCAT3,
            CODMARCHIO, TIPOMATERIALE, PESO, PREZZOLISTINO, ARTICOLOAQTA,
            STATO, CODNEGOZIO, CODCLIENTE, NUMFILIALE, NUMDOC, DATADOC,
            TIPODOC, DUPLICATO, utentemodifica, datamodifica
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload["BARCODE"],
        payload["CODART"],
        payload["DESCRIZIONE"],
        payload["CODCAT1"],
        payload["CODCAT2"],
        payload["CODCAT3"],
        payload["CODMARCHIO"],
        payload["TIPOMATERIALE"],
        payload["PESO"],
        payload["PREZZOLISTINO"],
        payload["ARTICOLOAQTA"],
        payload["STATO"],
        payload["CODNEGOZIO"],
        payload["CODCLIENTE"],
        payload["NUMFILIALE"],
        payload["NUMDOC"],
        payload["DATADOC"],
        payload["TIPODOC"],
        payload["DUPLICATO"],
        payload["utentemodifica"],
        payload["datamodifica"],
    )


def update_gs_articolo(cursor, codart, payload):
    # STATO non si aggiorna in modifica: resta quello impostato in INSERT (RIP).
    cursor.execute(
        """
        UPDATE GS_ARTICOLI SET
            BARCODE = ?,
            DESCRIZIONE = ?,
            CODCAT1 = ?,
            CODCAT2 = ?,
            PESO = ?,
            PREZZOLISTINO = ?,
            CODNEGOZIO = ?,
            CODCLIENTE = ?,
            NUMDOC = ?,
            DATADOC = ?,
            TIPODOC = ?,
            utentemodifica = ?,
            datamodifica = ?
        WHERE CODART = ?
        """,
        payload["BARCODE"],
        payload["DESCRIZIONE"],
        payload["CODCAT1"],
        payload["CODCAT2"],
        payload["PESO"],
        payload["PREZZOLISTINO"],
        payload["CODNEGOZIO"],
        payload["CODCLIENTE"],
        payload["NUMDOC"],
        payload["DATADOC"],
        payload["TIPODOC"],
        payload["utentemodifica"],
        payload["datamodifica"],
        codart,
    )
    return cursor.rowcount


def sync_pratica_to_gs_articoli(pratica, user):
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

    codart = (pratica.codice or "")[:20]
    if not codart:
        return GsArticoloSyncResult(
            ok=False,
            message="Codice riparazione mancante, impossibile sincronizzare GS_ARTICOLI.",
        )

    try:
        with open_mssql_connection(config) as connection:
            cursor = connection.cursor()
            created = False

            if gs_articolo_exists_by_codart(cursor, codart):
                barcode = resolve_gs_barcode(cursor, pratica, codart)
                payload = build_gs_articolo_payload(pratica, user, barcode)
                update_gs_articolo(cursor, codart, payload)
                message = f"Articolo GS aggiornato ({codart}, barcode {barcode})."
            else:
                barcode = resolve_gs_barcode(cursor, pratica, codart, for_insert=True)
                payload = build_gs_articolo_payload(pratica, user, barcode)
                insert_gs_articolo(cursor, payload)
                created = True
                message = f"Articolo GS creato ({codart}, barcode {barcode})."

            connection.commit()

        Pratica.objects.filter(pk=pratica.pk).update(gs_barcode=barcode)

        return GsArticoloSyncResult(
            ok=True,
            message=message,
            barcode=barcode,
            created=created,
        )
    except Exception as exc:
        return GsArticoloSyncResult(
            ok=False,
            message=f"Sincronizzazione GS_ARTICOLI non riuscita: {exc}",
        )
