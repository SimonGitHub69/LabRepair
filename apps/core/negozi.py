NEGOZI = (
    ("PT", "Pistoia"),
    ("MO", "Montale"),
    ("QU", "Quarrata"),
)

NEGOZI_MAP = dict(NEGOZI)
NEGOZI_CODES = set(NEGOZI_MAP)
NEGOZIO_FILTER_ALL = "all"

PRATICA_CODICE_PREFIX = {
    "PT": "P",
    "MO": "M",
    "QU": "Q",
}


def normalize_negozio_code(value):
    code = (value or "").strip().upper()
    if code in NEGOZI_CODES:
        return code
    return ""


def resolve_negozio_filter(raw_value, session_negozio):
    """
    Risolve il filtro negozio per elenchi riparazioni.
    Default: negozio di sessione. Solo con valore esplicito "all" mostra tutti.
    """
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
    return NEGOZI_MAP.get(normalize_negozio_code(code), "")
