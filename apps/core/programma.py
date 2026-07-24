from apps.core.models.configurazione_programma import GS_BARCODE_DEFAULT, ConfigurazioneProgramma


def get_configurazione_programma():
    return ConfigurazioneProgramma.get_solo()


def get_modalita_accettazione():
    return get_configurazione_programma().modalita_accettazione


def operatore_primo_nuova_riparazione():
    return get_configurazione_programma().operatore_primo_nuova_riparazione


def get_layout_stile(request=None):
    if request is not None:
        from apps.core.pc import get_configurazione_pc_for_request

        cfg_pc = get_configurazione_pc_for_request(request)
        if cfg_pc and cfg_pc.layout_stile:
            return cfg_pc.layout_stile
    return get_configurazione_programma().layout_stile or ConfigurazioneProgramma.LayoutStile.STANDARD


def layout_compatto(request=None):
    return get_layout_stile(request) == ConfigurazioneProgramma.LayoutStile.COMPATTA


def get_liste_righe_per_pagina():
    value = get_configurazione_programma().liste_righe_per_pagina
    try:
        return int(value)
    except (TypeError, ValueError):
        return 20


def comandi_voce_attivi():
    return bool(get_configurazione_programma().comandi_voce_attivi)


def get_comandi_voce_lingua():
    return (
        get_configurazione_programma().comandi_voce_lingua
        or ConfigurazioneProgramma.ComandiVoceLingua.IT_IT
    )


def get_comandi_voce_mappa():
    from apps.core.voice_commands import merge_voice_commands

    return merge_voice_commands(get_configurazione_programma().comandi_voce_mappa)


def get_comandi_voce_extra():
    from apps.core.voice_commands import normalize_extra_commands

    return normalize_extra_commands(get_configurazione_programma().comandi_voce_extra)


def get_gs_barcode_min():
    return get_configurazione_programma().barcode_iniziale or GS_BARCODE_DEFAULT


def get_webcam_tasto_scatto():
    return get_configurazione_programma().webcam_tasto_scatto or ""


def get_webcam_tasto_usa_foto():
    return get_configurazione_programma().webcam_tasto_usa_foto or ""


def get_webcam_tasto_nuovo_scatto():
    return get_configurazione_programma().webcam_tasto_nuovo_scatto or ""


def comunicazioni_mostra_allegato():
    return get_configurazione_programma().comunicazioni_mostra_allegato


def get_comunicazioni_formato_data():
    return get_configurazione_programma().comunicazioni_formato_data


def get_privacy_testo_diritti():
    return (get_configurazione_programma().privacy_testo_diritti or "").strip()


def get_privacy_testo_dichiarazione():
    return (get_configurazione_programma().privacy_testo_dichiarazione or "").strip()


DEFAULT_MAILTO_OGGETTO = "Riparazione {codice} - {cliente}"


def get_mailto_oggetto_template():
    value = (get_configurazione_programma().mailto_oggetto or "").strip()
    return value or DEFAULT_MAILTO_OGGETTO


def get_mailto_corpo_template():
    return (get_configurazione_programma().mailto_corpo or "").strip()


def _mailto_replacements(pratica):
    return {
        "{codice}": (getattr(pratica, "codice", None) or "").strip(),
        "{cliente}": (getattr(pratica, "cliente_label", None) or "").strip(),
        "{nome}": (getattr(pratica, "referente_nome", None) or "").strip(),
        "{cognome}": (getattr(pratica, "referente_cognome", None) or "").strip(),
        "{cellulare}": (getattr(pratica, "referente_cellulare", None) or "").strip(),
        "{telefono}": (getattr(pratica, "referente_telefono", None) or "").strip(),
    }


def _apply_mailto_placeholders(text, pratica):
    if not text:
        return ""
    for key, value in _mailto_replacements(pratica).items():
        text = text.replace(key, value)
    return text


def format_mailto_oggetto(pratica, template=None):
    text = template if template is not None else get_mailto_oggetto_template()
    text = _apply_mailto_placeholders(text, pratica)
    text = " ".join(text.split()).strip()
    if text:
        return text
    replacements = _mailto_replacements(pratica)
    return (
        DEFAULT_MAILTO_OGGETTO.replace("{codice}", replacements["{codice}"])
        .replace("{cliente}", replacements["{cliente}"])
        .strip()
    )


def format_mailto_corpo(pratica, template=None):
    text = template if template is not None else get_mailto_corpo_template()
    return _apply_mailto_placeholders(text, pratica).strip()


def build_mailto_href(email, pratica, oggetto_template=None, corpo_template=None):
    from urllib.parse import quote

    address = (email or "").strip()
    if not address:
        return ""

    subject = format_mailto_oggetto(pratica, template=oggetto_template)
    body = format_mailto_corpo(pratica, template=corpo_template)
    params = [f"subject={quote(subject)}"]
    if body:
        params.append(f"body={quote(body)}")
    return f"mailto:{address}?{'&'.join(params)}"


class _MailtoSample:
    codice = "P26-0001"
    referente_nome = "Mario"
    referente_cognome = "Rossi"
    referente_cellulare = "3331234567"
    referente_telefono = "0573123456"

    @property
    def cliente_label(self):
        return "Rossi Mario"


def get_mailto_preview(oggetto_template=None, corpo_template=None):
    sample = _MailtoSample()
    return {
        "oggetto": format_mailto_oggetto(sample, template=oggetto_template),
        "corpo": format_mailto_corpo(sample, template=corpo_template),
        "esempio_codice": sample.codice,
        "esempio_cliente": sample.cliente_label,
    }
