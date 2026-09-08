from django.conf import settings

from apps.core.negozi import negozio_label, normalize_negozio_code
from apps.core.pc import get_configurazione_pc_for_request, get_nome_pc_from_request
from apps.core.programma import get_configurazione_programma, get_layout_stile
from apps.core.version import get_version


def app_info(request):
    return {"app_version": get_version()}


def current_negozio(request):
    code = normalize_negozio_code(request.session.get("negozio"))
    return {
        "current_negozio_code": code,
        "current_negozio_label": negozio_label(code),
    }


def programma_settings(request):
    # Evita query inutili su login/logout (pagine senza layout app).
    path = getattr(request, "path", "") or ""
    if path.startswith(("/login/", "/logout/")):
        return {
            "webcam_tasto_scatto": "",
            "webcam_tasto_usa_foto": "",
            "webcam_tasto_nuovo_scatto": "",
            "comunicazioni_mostra_allegato": True,
            "comunicazioni_formato_data": "",
            "layout_stile": "standard",
            "liste_righe_per_pagina": 20,
            "comandi_voce_attivi": False,
            "comandi_voce_lingua": "it-IT",
            "comandi_voce_mappa": {},
            "comandi_voce_extra": [],
            "cie_reader_on_server": getattr(settings, "CIE_READER_ON_SERVER", True),
            "current_pc_name": "",
            "current_pc_label": "",
            "busta_stampa_senza_anteprima": False,
            "pratica_stato_radio": False,
            "pratica_tasto_salva": "",
            "pratica_tasto_annulla": "",
            "pratica_tasto_stampa_busta": "",
            "pratica_tasto_stampa_privacy": "",
        }

    cfg = get_configurazione_programma()
    cfg_pc = get_configurazione_pc_for_request(request)
    from apps.core.voice_commands import merge_voice_commands, normalize_extra_commands

    nome_pc = get_nome_pc_from_request(request)
    return {
        "webcam_tasto_scatto": cfg.webcam_tasto_scatto or "",
        "webcam_tasto_usa_foto": cfg.webcam_tasto_usa_foto or "",
        "webcam_tasto_nuovo_scatto": cfg.webcam_tasto_nuovo_scatto or "",
        "comunicazioni_mostra_allegato": cfg.comunicazioni_mostra_allegato,
        "comunicazioni_formato_data": cfg.comunicazioni_formato_data,
        "layout_stile": get_layout_stile(request),
        "liste_righe_per_pagina": cfg.liste_righe_per_pagina or 20,
        "comandi_voce_attivi": bool(cfg.comandi_voce_attivi),
        "comandi_voce_lingua": cfg.comandi_voce_lingua or "it-IT",
        "comandi_voce_mappa": merge_voice_commands(cfg.comandi_voce_mappa),
        "comandi_voce_extra": normalize_extra_commands(cfg.comandi_voce_extra),
        "cie_reader_on_server": getattr(settings, "CIE_READER_ON_SERVER", True),
        "current_pc_name": nome_pc,
        "current_pc_label": str(cfg_pc) if cfg_pc else nome_pc,
        "busta_stampa_senza_anteprima": bool(
            getattr(cfg_pc, "busta_stampa_senza_anteprima", False)
        ),
        "pratica_stato_radio": bool(getattr(cfg_pc, "pratica_stato_radio", False)),
        "pratica_tasto_salva": getattr(cfg_pc, "pratica_tasto_salva", "") or "",
        "pratica_tasto_annulla": getattr(cfg_pc, "pratica_tasto_annulla", "") or "",
        "pratica_tasto_stampa_busta": getattr(cfg_pc, "pratica_tasto_stampa_busta", "")
        or "",
        "pratica_tasto_stampa_privacy": getattr(cfg_pc, "pratica_tasto_stampa_privacy", "")
        or "",
    }
