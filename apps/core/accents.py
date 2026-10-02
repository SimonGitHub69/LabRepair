"""Ricerca testo ignorando accenti (es. Filie → Filiè)."""

from __future__ import annotations

import unicodedata

from django.db.models import CharField, F, Func, Q, Value
from django.db.models.functions import Coalesce, Lower

# translate() dopo lower(): solo minuscole accentate → ASCII.
_ACCENT_FROM = "àáâäãåèéêëìíîïòóôöõùúûüçñýÿ"
_ACCENT_TO = "aaaaaaeeeeiiiiooooouuuucnyy"


def fold_accents(text: str) -> str:
    """Rimuove diacritici e normalizza in minuscolo (lato Python / query)."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    decomposed = unicodedata.normalize("NFD", raw)
    return "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    ).casefold()


class AccentFold(Func):
    """PostgreSQL/SQLite: translate(lower(campo), accenti, ascii)."""

    function = "translate"
    output_field = CharField()

    def __init__(self, expression, **extra):
        super().__init__(
            Lower(expression),
            Value(_ACCENT_FROM),
            Value(_ACCENT_TO),
            **extra,
        )


def annotate_accent_folds(queryset, field_map: dict[str, str]):
    """
    Annota queryset con alias piegati.
    field_map: {alias: 'campo_o_path'} es. {'_af_cognome': 'referente_cognome'}
    """
    annotations = {}
    for alias, field_name in field_map.items():
        annotations[alias] = AccentFold(Coalesce(F(field_name), Value("")))
    return queryset.annotate(**annotations)


def q_accent_icontains(alias: str, folded_query: str) -> Q:
    if not folded_query:
        return Q()
    return Q(**{f"{alias}__icontains": folded_query})


def build_accent_search_q(folded_query: str, aliases: list[str]) -> Q:
    if not folded_query or not aliases:
        return Q()
    combined = q_accent_icontains(aliases[0], folded_query)
    for alias in aliases[1:]:
        combined |= q_accent_icontains(alias, folded_query)
    return combined
