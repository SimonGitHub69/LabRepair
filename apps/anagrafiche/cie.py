"""Lettura CIE tramite helper locale cie_reader.exe (PC/SC + PACE/CAN)."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

CAN_RE = re.compile(r"^\d{6}$")

FORM_FIELDS = (
    "cognome",
    "nome",
    "sesso",
    "data_nascita",
    "luogo_nascita",
    "provincia_nascita",
    "codice_fiscale",
    "documento_tipo",
    "documento_numero",
    "documento_data_rilascio",
    "documento_data_scadenza",
    "documento_rilasciato_da",
)

INDIRIZZO_FIELDS = (
    "indirizzo",
    "civico",
    "cap",
    "comune",
    "provincia",
)


class CieReadError(Exception):
    """Errore di lettura CIE."""


def get_cie_reader_exe() -> Path:
    configured = getattr(settings, "CIE_READER_EXE", None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / "tools" / "cie_reader" / "publish" / "cie_reader.exe"


def map_cie_payload(raw: dict) -> dict:
    """Mappa l'output dell'helper ai campi del form anagrafica."""
    data = {key: (raw.get(key) or "").strip() for key in FORM_FIELDS}
    if not data.get("documento_tipo"):
        data["documento_tipo"] = "Carta di Identità"
    if data.get("codice_fiscale"):
        data["codice_fiscale"] = data["codice_fiscale"].upper()
    if data.get("provincia_nascita"):
        data["provincia_nascita"] = data["provincia_nascita"][:2].upper()

    indirizzo = {
        "indirizzo": (raw.get("indirizzo") or "").strip(),
        "civico": (raw.get("civico") or "").strip(),
        "cap": (raw.get("cap") or "").strip(),
        "comune": (raw.get("comune") or "").strip(),
        "provincia": (raw.get("provincia") or "").strip()[:2].upper(),
        "tipo": "residenza",
    }

    # Fallback CAP dalla stringa grezza del chip se il parser non l'ha isolato
    raw_address = (raw.get("indirizzo_raw") or raw.get("chip_indirizzo") or "").strip()
    if not indirizzo["cap"] and raw_address:
        match = re.search(r"\b(\d{5})\b", raw_address)
        if match:
            indirizzo["cap"] = match.group(1)

    # Rilasciato da: mai "Ministero"; usa il Comune di residenza sul chip
    rilasciato = (data.get("documento_rilasciato_da") or "").strip()
    if not rilasciato or "MINISTERO" in rilasciato.upper():
        comune = indirizzo["comune"]
        if comune:
            if comune.upper().startswith("COMUNE"):
                data["documento_rilasciato_da"] = comune
            else:
                data["documento_rilasciato_da"] = f"Comune di {comune}"

    if any(indirizzo[k] for k in ("indirizzo", "comune", "cap", "provincia")):
        indirizzo["indirizzo_raw"] = raw_address
        data["indirizzo"] = indirizzo
        data["indirizzo_raw"] = raw_address
    else:
        data["indirizzo"] = None
        data["indirizzo_raw"] = raw_address

    return data


def read_cie(can: str, *, timeout: int = 45) -> dict:
    can = (can or "").strip()
    if not CAN_RE.match(can):
        raise CieReadError("Il CAN deve essere composto da 6 cifre.")

    exe = get_cie_reader_exe()
    if not exe.is_file():
        raise CieReadError(
            "Helper lettura CIE non trovato. Esegui tools/cie_reader/build.ps1 "
            f"(atteso: {exe})."
        )

    try:
        completed = subprocess.run(
            [str(exe), "--can", can, "--timeout", "20"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(exe.parent),
        )
    except subprocess.TimeoutExpired as exc:
        raise CieReadError(
            "Timeout durante la lettura della CIE. Tieni la carta sul lettore e riprova."
        ) from exc
    except OSError as exc:
        raise CieReadError(f"Impossibile avviare il lettore CIE: {exc}") from exc

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()

    if completed.returncode != 0:
        message = _extract_error_message(stderr, stdout) or (
            "Lettura CIE non riuscita. Verifica CAN, carta e lettore Bit4id."
        )
        logger.warning("cie_reader failed rc=%s stderr=%s", completed.returncode, stderr)
        raise CieReadError(message)

    if not stdout:
        raise CieReadError("Nessun dato restituito dal lettore CIE.")

    try:
        raw = json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError as exc:
        logger.warning("cie_reader invalid JSON: %s", stdout[:500])
        raise CieReadError("Risposta del lettore CIE non valida.") from exc

    if not isinstance(raw, dict):
        raise CieReadError("Risposta del lettore CIE non valida.")

    return map_cie_payload(raw)


def _extract_error_message(stderr: str, stdout: str) -> str:
    for blob in (stderr, stdout):
        if not blob:
            continue
        for line in reversed(blob.splitlines()):
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = (payload.get("message") or "").strip()
                if message:
                    return message
            else:
                return line
    return ""
