from django.db.models import Q
from django.utils import timezone

from apps.core.negozi import get_pratica_codice_prefix, normalize_negozio_code
from apps.pratiche.models import Pratica


def _codice_prefixes_for_negozio(negozio, year_suffix):
    negozio = normalize_negozio_code(negozio)
    if not negozio:
        return []

    current_prefix = f"{get_pratica_codice_prefix(negozio)}{year_suffix:02d}-"
    legacy_prefix = f"{negozio}{year_suffix:02d}-"
    if legacy_prefix == current_prefix:
        return [current_prefix]
    return [current_prefix, legacy_prefix]


def _progressive_from_codice(codice):
    try:
        return int(str(codice).rsplit("-", 1)[-1])
    except (TypeError, ValueError):
        return None


def _max_progressive_for_prefixes(prefixes):
    if not prefixes:
        return 0

    query = Q()
    for prefix in prefixes:
        query |= Q(codice__startswith=prefix)

    max_progressive = 0
    for codice in Pratica.objects.filter(query).values_list("codice", flat=True):
        progressive = _progressive_from_codice(codice)
        if progressive is not None and progressive > max_progressive:
            max_progressive = progressive
    return max_progressive


def get_next_pratica_codice(negozio):
    negozio = normalize_negozio_code(negozio)
    if not negozio:
        return ""

    year_suffix = timezone.localdate().year % 100
    prefixes = _codice_prefixes_for_negozio(negozio, year_suffix)
    next_number = _max_progressive_for_prefixes(prefixes) + 1
    prefix = f"{get_pratica_codice_prefix(negozio)}{year_suffix:02d}-"
    return f"{prefix}{next_number:04d}"


def reserve_pratica_codice(negozio, reserved_codice=""):
    negozio = normalize_negozio_code(negozio)
    if not negozio:
        raise ValueError("Impossibile generare il codice riparazione senza negozio valido.")

    reserved_codice = (reserved_codice or "").strip()
    year_suffix = timezone.localdate().year % 100
    expected_prefix = f"{get_pratica_codice_prefix(negozio)}{year_suffix:02d}-"

    if reserved_codice.startswith(expected_prefix) and not Pratica.objects.filter(codice=reserved_codice).exists():
        return reserved_codice

    for _ in range(20):
        candidate = get_next_pratica_codice(negozio)
        if not Pratica.objects.filter(codice=candidate).exists():
            return candidate

    raise ValueError("Impossibile riservare un codice riparazione univoco.")
