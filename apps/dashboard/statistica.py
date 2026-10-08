"""Statistica riparazioni acquisite, per negozio e per periodo."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncYear
from django.utils import timezone

from apps.core.negozi import negozi_choices, negozio_label
from apps.pratiche.models import Pratica

GRANULARITA = ("giorno", "mese", "anno")
METRICHE = ("numero", "prezzo_pubblico", "prezzo_pagato", "costo_totale")
_ZERO_MONEY = Value(Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))

_MAX_BUCKETS = {
    "giorno": 120,
    "mese": 36,
    "anno": 20,
}

_MESI = (
    "gen",
    "feb",
    "mar",
    "apr",
    "mag",
    "giu",
    "lug",
    "ago",
    "set",
    "ott",
    "nov",
    "dic",
)


def _parse_date(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def default_period(granularita, today=None):
    today = today or timezone.localdate()
    if granularita == "mese":
        index = today.year * 12 + today.month - 1 - 11
        return date(index // 12, index % 12 + 1, 1), today
    if granularita == "anno":
        return date(today.year - 4, 1, 1), today
    return today - timedelta(days=29), today


def resolve_period(granularita, dal_raw="", al_raw="", today=None):
    today = today or timezone.localdate()
    default_dal, default_al = default_period(granularita, today)
    dal = _parse_date(dal_raw) or default_dal
    al = _parse_date(al_raw) or default_al
    if dal > al:
        dal, al = al, dal

    max_buckets = _MAX_BUCKETS[granularita]
    if granularita == "giorno" and (al - dal).days + 1 > max_buckets:
        dal = al - timedelta(days=max_buckets - 1)
    elif granularita == "mese":
        months = (al.year - dal.year) * 12 + (al.month - dal.month) + 1
        if months > max_buckets:
            index = al.year * 12 + al.month - 1 - (max_buckets - 1)
            dal = date(index // 12, index % 12 + 1, 1)
    elif granularita == "anno" and (al.year - dal.year + 1) > max_buckets:
        dal = date(al.year - (max_buckets - 1), 1, 1)
    return dal, al


def _buckets(granularita, dal, al):
    if granularita == "giorno":
        current = dal
        while current <= al:
            yield current
            current += timedelta(days=1)
        return
    if granularita == "mese":
        year, month = dal.year, dal.month
        end = (al.year, al.month)
        while (year, month) <= end:
            yield date(year, month, 1)
            month += 1
            if month == 13:
                month = 1
                year += 1
        return
    for year in range(dal.year, al.year + 1):
        yield date(year, 1, 1)


def format_bucket_label(granularita, bucket, *, with_year=False):
    if granularita == "giorno":
        return bucket.strftime("%d/%m/%y" if with_year else "%d/%m")
    if granularita == "mese":
        return f"{_MESI[bucket.month - 1]} {bucket.year}"
    return str(bucket.year)


def _money(value):
    return float(Decimal(value or 0).quantize(Decimal("0.01")))


def _bucket_key(granularita, value):
    if value is None:
        return None
    if hasattr(value, "date"):
        value = value.date()
    if granularita == "mese":
        return date(value.year, value.month, 1)
    if granularita == "anno":
        return date(value.year, 1, 1)
    return value


def build_statistica(granularita, dal, al):
    trunc = {
        "giorno": TruncDay,
        "mese": TruncMonth,
        "anno": TruncYear,
    }[granularita]
    rows = (
        Pratica.objects.filter(
            is_active=True,
            data_apertura__gte=dal,
            data_apertura__lte=al,
        )
        .annotate(bucket=trunc("data_apertura"))
        .values("bucket", "negozio")
        .annotate(
            numero=Count("id"),
            prezzo_pubblico=Sum("prezzo_al"),
            prezzo_pagato=Sum("prezzo_pagato"),
            costo_totale=Sum(
                Coalesce(F("costo_lavorazione"), _ZERO_MONEY)
                + Coalesce(F("costo_materiale"), _ZERO_MONEY)
                + Coalesce(F("oro_aggiunto"), _ZERO_MONEY)
                * Coalesce(F("prezzo_unita"), _ZERO_MONEY)
            ),
        )
    )

    buckets = list(_buckets(granularita, dal, al))
    index = {bucket: position for position, bucket in enumerate(buckets)}
    store_codes = [code for code, _label in negozi_choices()]
    seen = set(store_codes)
    extra = sorted(
        {
            (row["negozio"] or "")
            for row in rows
            if (row["negozio"] or "") not in seen
        }
    )
    store_codes.extend(extra)

    def empty_series(code):
        label = negozio_label(code) or (code or "Senza negozio")
        zeros = [0] * len(buckets)
        return {
            "codice": code,
            "label": label,
            "numero": zeros[:],
            "prezzo_pubblico": zeros[:],
            "prezzo_pagato": zeros[:],
            "costo_totale": zeros[:],
        }

    series_by_code = {code: empty_series(code) for code in store_codes}
    for row in rows:
        key = _bucket_key(granularita, row["bucket"])
        position = index.get(key)
        if position is None:
            continue
        code = row["negozio"] or ""
        series = series_by_code.setdefault(code, empty_series(code))
        series["numero"][position] = int(row["numero"] or 0)
        series["prezzo_pubblico"][position] = _money(row["prezzo_pubblico"])
        series["prezzo_pagato"][position] = _money(row["prezzo_pagato"])
        series["costo_totale"][position] = _money(row["costo_totale"])

    ordered = [series_by_code[code] for code in store_codes if code in series_by_code]
    for code, series in series_by_code.items():
        if code not in store_codes:
            ordered.append(series)

    return {
        "granularita": granularita,
        "dal": dal.isoformat(),
        "al": al.isoformat(),
        "labels": [
            format_bucket_label(
                granularita,
                bucket,
                with_year=dal.year != al.year,
            )
            for bucket in buckets
        ],
        "series": ordered,
    }


def statistica_from_query(granularita_raw, dal_raw="", al_raw=""):
    granularita = (granularita_raw or "mese").strip().lower()
    if granularita not in GRANULARITA:
        granularita = "mese"
    dal, al = resolve_period(granularita, dal_raw, al_raw)
    return granularita, dal, al, build_statistica(granularita, dal, al)
