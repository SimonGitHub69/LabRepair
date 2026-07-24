from datetime import date, datetime

from django import forms
from django.utils import timezone


CURRENT_YEAR_VALIDATION_MESSAGE = "La data deve essere nell'anno corrente ({year})."


def current_year():
    return timezone.localdate().year


def current_year_start():
    return date(current_year(), 1, 1)


def current_year_end():
    return date(current_year(), 12, 31)


def normalize_date_value(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def is_unchanged_date(instance, field_name, value):
    if not instance or not getattr(instance, "pk", None):
        return False

    original = getattr(instance, field_name, None)
    if original is None:
        return False

    return normalize_date_value(original) == normalize_date_value(value)


def validate_current_year_date(value, *, instance=None, field_name=None):
    check = normalize_date_value(value)
    if check is None:
        return

    year = current_year()
    if check.year == year:
        return

    if instance and field_name and is_unchanged_date(instance, field_name, check):
        return

    raise forms.ValidationError(CURRENT_YEAR_VALIDATION_MESSAGE.format(year=year))


def apply_current_year_date_widget(field, *, min_date=None, instance_value=None):
    instance_value = normalize_date_value(instance_value)
    year = current_year()

    if instance_value and instance_value.year != year:
        if min_date:
            field.widget.attrs["min"] = min_date.isoformat()
        field.widget.attrs["data-current-year"] = "true"
        return

    effective_min = current_year_start()
    if min_date and min_date > effective_min:
        effective_min = min_date
    if (
        min_date
        and instance_value
        and instance_value.year == year
        and instance_value < effective_min
    ):
        effective_min = instance_value

    field.widget.attrs["min"] = effective_min.isoformat()
    field.widget.attrs["max"] = current_year_end().isoformat()
    field.widget.attrs["data-current-year"] = "true"


def apply_current_year_datetime_widget(field, *, instance_value=None):
    instance_date = normalize_date_value(instance_value)
    year = current_year()

    if instance_date and instance_date.year != year:
        field.widget.attrs["data-current-year"] = "true"
        return

    start = current_year_start().isoformat()
    end = current_year_end().isoformat()
    field.widget.attrs["min"] = f"{start}T00:00"
    field.widget.attrs["max"] = f"{end}T23:59"
    field.widget.attrs["data-current-year"] = "true"
