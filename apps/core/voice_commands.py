"""Default e merge delle frasi per i comandi vocali."""

from __future__ import annotations

VOICE_COMMAND_DEFINITIONS = [
    {
        "key": "nuova_riparazione",
        "label": "Nuova riparazione",
        "hint": "Apre la maschera Nuova riparazione",
        "defaults": ["nuova riparazione", "nuova pratica", "apri nuova riparazione"],
    },
    {
        "key": "nuovo_cliente",
        "label": "Nuovo cliente",
        "hint": "Apre Nuova anagrafica cliente",
        "defaults": ["nuovo cliente", "nuova anagrafica"],
    },
    {
        "key": "riparazioni",
        "label": "Elenco riparazioni",
        "hint": "Vai all'elenco riparazioni",
        "defaults": ["riparazioni", "elenco riparazioni", "pratiche", "vai alle riparazioni"],
    },
    {
        "key": "anagrafiche",
        "label": "Elenco anagrafiche",
        "hint": "Vai all'elenco anagrafiche/clienti",
        "defaults": ["anagrafiche", "clienti", "elenco anagrafiche", "vai alle anagrafiche"],
    },
    {
        "key": "agenda",
        "label": "Agenda",
        "hint": "Apre il calendario agenda",
        "defaults": ["agenda", "calendario"],
    },
    {
        "key": "dashboard",
        "label": "Dashboard",
        "hint": "Torna alla home",
        "defaults": ["dashboard", "home", "inizio"],
    },
    {
        "key": "parametri",
        "label": "Parametri programma",
        "hint": "Apre i parametri programma",
        "defaults": ["parametri", "parametri programma", "apri parametri"],
    },
    {
        "key": "comandi_vocali",
        "label": "Comandi vocali",
        "hint": "Apre la pagina di configurazione dei comandi vocali",
        "defaults": ["comandi vocali", "parametri vocali", "apri comandi vocali"],
    },
    {
        "key": "pagina_successiva",
        "label": "Pagina successiva",
        "hint": "Nella lista: pagina dopo",
        "defaults": ["pagina successiva", "avanti", "pagina dopo"],
    },
    {
        "key": "pagina_precedente",
        "label": "Pagina precedente",
        "hint": "Nella lista: pagina prima",
        "defaults": ["pagina precedente", "indietro", "pagina prima"],
    },
    {
        "key": "prima_pagina",
        "label": "Prima pagina",
        "hint": "Nella lista: vai alla prima pagina",
        "defaults": ["prima pagina"],
    },
    {
        "key": "ultima_pagina",
        "label": "Ultima pagina",
        "hint": "Nella lista: vai all'ultima pagina",
        "defaults": ["ultima pagina"],
    },
    {
        "key": "vai_pagina",
        "label": "Vai a pagina N",
        "hint": "Prefissi per «… 3» (es. vai alla pagina, pagina)",
        "defaults": ["vai alla pagina", "vai a pagina", "pagina"],
    },
    {
        "key": "cerca",
        "label": "Cerca",
        "hint": "Prefissi per «… Rossi» (cerca nelle riparazioni; oppure «cerca cliente …»)",
        "defaults": ["cerca", "ricerca", "trova"],
    },
    {
        "key": "aiuto",
        "label": "Aiuto comandi",
        "hint": "Mostra il riepilogo dei comandi",
        "defaults": ["aiuto", "help", "comandi vocali", "elenco comandi"],
    },
]

VOICE_COMMAND_DEFAULTS = {
    item["key"]: list(item["defaults"]) for item in VOICE_COMMAND_DEFINITIONS
}

# Destinazioni selezionabili per comandi personalizzati (oltre a URL libero).
VOICE_DESTINATION_CHOICES = [
    ("riparazioni", "Elenco riparazioni"),
    ("nuova_riparazione", "Nuova riparazione"),
    ("anagrafiche", "Elenco anagrafiche"),
    ("nuovo_cliente", "Nuovo cliente"),
    ("agenda", "Agenda"),
    ("dashboard", "Dashboard"),
    ("parametri", "Parametri programma"),
    ("comandi_vocali", "Comandi vocali"),
    ("operatori", "Operatori"),
    ("tipi_oggetto", "Tipi di oggetto"),
    ("aziende", "Aziende"),
    ("sistema", "Sistema"),
    ("webcam", "Webcam"),
    ("non_ritirate", "Riparazioni: Non ritirate"),
    ("ritardo_lavorazione", "Riparazioni: Ritardo lavorazione"),
    ("url", "URL personalizzato"),
]

VOICE_BUILTIN_DESTINATION_KEYS = {
    value for value, _label in VOICE_DESTINATION_CHOICES if value != "url"
}


def parse_voice_phrases(value: str | None) -> list[str]:
    if not value:
        return []
    seen = set()
    result = []
    for part in str(value).split(","):
        phrase = " ".join(part.split()).strip()
        if not phrase:
            continue
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(phrase)
    return result


def phrases_to_text(phrases: list[str] | None) -> str:
    return ", ".join(phrases or [])


def sanitize_internal_url(value: str | None) -> str:
    url = (value or "").strip()
    if not url:
        return ""
    if not url.startswith("/") or url.startswith("//"):
        return ""
    if any(ch in url for ch in ("\n", "\r", " ")):
        return ""
    return url


def merge_voice_commands(stored: dict | None) -> dict[str, list[str]]:
    """Restituisce la mappa effettiva (custom se valorizzata, altrimenti default)."""
    stored = stored if isinstance(stored, dict) else {}
    merged: dict[str, list[str]] = {}
    for key, defaults in VOICE_COMMAND_DEFAULTS.items():
        custom = stored.get(key)
        if isinstance(custom, list) and custom:
            cleaned = []
            seen = set()
            for item in custom:
                phrase = " ".join(str(item).split()).strip()
                if not phrase:
                    continue
                norm = phrase.casefold()
                if norm in seen:
                    continue
                seen.add(norm)
                cleaned.append(phrase)
            merged[key] = cleaned or list(defaults)
        else:
            merged[key] = list(defaults)
    return merged


def voice_commands_for_form(stored: dict | None) -> dict[str, str]:
    """Valori testo (virgola-separati) per i campi del form Parametri."""
    merged = merge_voice_commands(stored)
    if not isinstance(stored, dict) or not stored:
        return {key: phrases_to_text(phrases) for key, phrases in merged.items()}
    result = {}
    for key, defaults in VOICE_COMMAND_DEFAULTS.items():
        custom = stored.get(key)
        if isinstance(custom, list) and custom:
            result[key] = phrases_to_text(custom)
        else:
            result[key] = phrases_to_text(defaults)
    return result


def normalize_extra_commands(raw) -> list[dict]:
    """Normalizza i comandi personalizzati salvati."""
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        phrases = parse_voice_phrases(
            phrases_to_text(item.get("phrases"))
            if isinstance(item.get("phrases"), list)
            else item.get("phrases")
        )
        if not phrases and isinstance(item.get("frasi"), (list, str)):
            phrases = parse_voice_phrases(
                phrases_to_text(item.get("frasi"))
                if isinstance(item.get("frasi"), list)
                else item.get("frasi")
            )
        if not phrases:
            continue
        destinazione = (item.get("destinazione") or item.get("target") or "").strip()
        url = sanitize_internal_url(item.get("url"))
        etichetta = " ".join(str(item.get("etichetta") or item.get("label") or "").split()).strip()
        if destinazione == "url" or (not destinazione and url):
            if not url:
                continue
            destinazione = "url"
        elif destinazione not in VOICE_BUILTIN_DESTINATION_KEYS:
            continue
        result.append(
            {
                "frasi": phrases,
                "destinazione": destinazione,
                "url": url if destinazione == "url" else "",
                "etichetta": etichetta,
            }
        )
    return result
