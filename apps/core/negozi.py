FALLBACK_NEGOZI = (
    ("PT", "Pistoia"),
    ("MO", "Montale"),
    ("QU", "Quarrata"),
)

FALLBACK_PREFIX = {
    "PT": "P",
    "MO": "M",
    "QU": "Q",
}

FALLBACK_LOCALITA = {
    "PT": "PISTOIA",
    "MO": "MONTALE",
    "QU": "QUARRATA",
}

NEGOZIO_FILTER_ALL = "all"

_cache_rows = None

NEGOZI = list(FALLBACK_NEGOZI)
NEGOZI_MAP = dict(FALLBACK_NEGOZI)
NEGOZI_CODES = set(NEGOZI_MAP)
PRATICA_CODICE_PREFIX = dict(FALLBACK_PREFIX)


def _load_negozi_rows(force=False):
    global _cache_rows
    if _cache_rows is not None and not force:
        return _cache_rows
    try:
        from apps.core.models.negozio import Negozio

        rows = list(
            Negozio.objects.filter(is_active=True)
            .order_by("ordine", "codice")
            .values_list(
                "codice",
                "denominazione",
                "prefisso_pratica",
                "localita_privacy",
                "ddt_sezionale",
                "ddt_numero_iniziale",
            )
        )
        if rows:
            _cache_rows = rows
            return _cache_rows
    except Exception:
        pass
    _cache_rows = [
        (
            code,
            label,
            FALLBACK_PREFIX.get(code, code[:1]),
            FALLBACK_LOCALITA.get(code, ""),
            "R",
            1,
        )
        for code, label in FALLBACK_NEGOZI
    ]
    return _cache_rows


def negozi_choices():
    """Callable choices for model/form fields (tabella Negozi)."""
    return tuple((code, label) for code, label, *_rest in _load_negozi_rows())


def refresh_negozi_cache():
    global NEGOZI_MAP, NEGOZI_CODES, PRATICA_CODICE_PREFIX
    rows = _load_negozi_rows(force=True)
    NEGOZI.clear()
    NEGOZI.extend((code, label) for code, label, *_rest in rows)
    NEGOZI_MAP = dict(NEGOZI)
    NEGOZI_CODES = set(NEGOZI_MAP)
    PRATICA_CODICE_PREFIX = {
        code: (prefisso or code[:1]).upper()
        for code, _label, prefisso, *_rest in rows
    }
    return NEGOZI


def normalize_negozio_code(value):
    if _cache_rows is None:
        refresh_negozi_cache()
    code = (value or "").strip().upper()
    if code in NEGOZI_CODES:
        return code
    return ""


def resolve_negozio_filter(raw_value, session_negozio):
    raw = (raw_value or "").strip()
    if raw.lower() == NEGOZIO_FILTER_ALL:
        return NEGOZIO_FILTER_ALL
    code = normalize_negozio_code(raw)
    if code:
        return code
    return normalize_negozio_code(session_negozio) or NEGOZIO_FILTER_ALL


def apply_negozio_queryset_filter(queryset, negozio_filter, field="negozio"):
    if negozio_filter and negozio_filter != NEGOZIO_FILTER_ALL:
        return queryset.filter(**{field: negozio_filter})
    return queryset


def get_pratica_codice_prefix(negozio):
    code = normalize_negozio_code(negozio)
    if not code:
        return ""
    return PRATICA_CODICE_PREFIX.get(code, code[:1])


def negozio_label(code):
    if code == NEGOZIO_FILTER_ALL:
        return "Tutti i negozi"
    if _cache_rows is None:
        refresh_negozi_cache()
    return NEGOZI_MAP.get(normalize_negozio_code(code), "")


def get_negozio_localita(code):
    code = normalize_negozio_code(code)
    if not code:
        return ""
    for row_code, _label, _prefisso, localita, *_rest in _load_negozi_rows():
        if row_code == code:
            return (localita or "").strip() or FALLBACK_LOCALITA.get(code, "")
    return FALLBACK_LOCALITA.get(code, "")


def get_negozio_ddt_settings(code):
    """Restituisce (sezionale, numero_iniziale) per la numerazione DDT del negozio."""
    from apps.core.programma import get_configurazione_programma

    code = normalize_negozio_code(code)
    cfg = get_configurazione_programma()
    sezionale_fallback = (getattr(cfg, "ddt_sezionale", None) or "R").strip().upper() or "R"
    try:
        iniziale_fallback = max(1, int(getattr(cfg, "ddt_numero_iniziale", 1) or 1))
    except (TypeError, ValueError):
        iniziale_fallback = 1

    if not code:
        return sezionale_fallback, iniziale_fallback

    try:
        from apps.core.models.negozio import Negozio

        row = (
            Negozio.objects.filter(is_active=True, codice=code)
            .only("ddt_sezionale", "ddt_numero_iniziale")
            .first()
        )
        if row:
            sezionale = (row.ddt_sezionale or "").strip().upper() or sezionale_fallback
            try:
                iniziale = max(1, int(row.ddt_numero_iniziale or iniziale_fallback))
            except (TypeError, ValueError):
                iniziale = iniziale_fallback
            return sezionale, iniziale
    except Exception:
        pass

    return sezionale_fallback, iniziale_fallback
