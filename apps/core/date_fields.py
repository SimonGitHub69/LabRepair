from datetime import date, datetime

from django import forms
from django.utils import timezone


CURRENT_YEAR_VALIDATION_MESSAGE = "La data deve essere nell'anno corrente ({year})."
YEAR_RANGE_VALIDATION_MESSAGE = (
    "La data deve essere compresa tra il {min_year} e il {max_year}."
)
NOT_BEFORE_TODAY_MESSAGE = "La data prevista consegna non può essere precedente a oggi."

# Limiti date scheda Riparazione (Pratica).
PRATICA_DATE_MIN_YEAR = 2026
PRATICA_DATE_MAX_YEAR = 2099

# Data di nascita: età ammissibile e tetto assoluto (errori di anno).
NASCITA_ETA_MIN = 6
NASCITA_ETA_MAX = 100
NASCITA_ETA_LIMITE = 120
NASCITA_FUTURA_MESSAGE = "La data di nascita non può essere successiva a oggi."
NASCITA_TROPPO_VECCHIA_MESSAGE = (
    "Data di nascita non valida: l'età risulterebbe superiore a {limit} anni."
)
NASCITA_OLTRE_MAX_MESSAGE = (
    "Controlla la data di nascita: l'età risulta di {age} anni (oltre {max_age})."
)
NASCITA_SOTTO_MIN_MESSAGE = (
    "Controlla la data di nascita: l'età risulta di {age_label} (inferiore a {min_age} anni)."
)


def current_year():
    return timezone.localdate().year


def current_year_start():
    return date(current_year(), 1, 1)


def current_year_end():
    return date(current_year(), 12, 31)


def year_range_start(min_year):
    return date(int(min_year), 1, 1)


def year_range_end(max_year):
    return date(int(max_year), 12, 31)


def pratica_date_min():
    return year_range_start(PRATICA_DATE_MIN_YEAR)


def pratica_date_max():
    return year_range_end(PRATICA_DATE_MAX_YEAR)


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


def validate_year_range_date(
    value,
    *,
    min_year,
    max_year,
    instance=None,
    field_name=None,
):
    check = normalize_date_value(value)
    if check is None:
        return

    if min_year <= check.year <= max_year:
        return

    if instance and field_name and is_unchanged_date(instance, field_name, check):
        return

    raise forms.ValidationError(
        YEAR_RANGE_VALIDATION_MESSAGE.format(min_year=min_year, max_year=max_year)
    )


def validate_pratica_date(value, *, instance=None, field_name=None):
    validate_year_range_date(
        value,
        min_year=PRATICA_DATE_MIN_YEAR,
        max_year=PRATICA_DATE_MAX_YEAR,
        instance=instance,
        field_name=field_name,
    )


def validate_not_before_today(value, *, instance=None, field_name=None, message=None):
    """Rifiuta date precedenti a oggi (usata solo in creazione Nuova riparazione)."""
    check = normalize_date_value(value)
    if check is None:
        return

    today = timezone.localdate()
    if check >= today:
        return

    raise forms.ValidationError(message or NOT_BEFORE_TODAY_MESSAGE)


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


def apply_year_range_date_widget(
    field,
    *,
    min_year,
    max_year,
    min_date=None,
    instance_value=None,
):
    """Imposta min/max HTML sul date picker (anni inclusivi)."""
    instance_value = normalize_date_value(instance_value)
    min_date = normalize_date_value(min_date)
    range_min = year_range_start(min_year)
    range_max = year_range_end(max_year)

    # Con min_date (es. oggi): usa il più restrittivo tra range e data minima.
    # Se "oggi" è prima dell'inizio range, resta comunque oggi (il JS può
    # riallineare al calendario del PC).
    effective_min = range_min
    if min_date is not None:
        effective_min = max(range_min, min_date) if min_date >= range_min else min_date

    # Con min_date (es. oggi per consegna): non allargare il picker sotto oggi
    # anche se in scheda c'è ancora una data passata.
    if instance_value and instance_value < effective_min and min_date is None:
        effective_min = instance_value
    effective_max = range_max
    if instance_value and instance_value > effective_max:
        effective_max = instance_value

    field.widget.attrs["min"] = effective_min.isoformat()
    field.widget.attrs["max"] = effective_max.isoformat()
    field.widget.attrs["data-date-min-year"] = str(min_year)
    field.widget.attrs["data-date-max-year"] = str(max_year)
    if min_date is not None:
        field.widget.attrs["data-consegna-not-before-today"] = "1"


def apply_pratica_date_widget(field, *, min_date=None, instance_value=None):
    apply_year_range_date_widget(
        field,
        min_year=PRATICA_DATE_MIN_YEAR,
        max_year=PRATICA_DATE_MAX_YEAR,
        min_date=min_date,
        instance_value=instance_value,
    )


def shift_years(base, years):
    base = normalize_date_value(base)
    try:
        return date(base.year + years, base.month, base.day)
    except ValueError:
        return date(base.year + years, 2, 28)


def age_in_years(born, today=None):
    born = normalize_date_value(born)
    if born is None:
        return None
    today = normalize_date_value(today) or timezone.localdate()
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    return years


def format_age_label(age):
    if age <= 0:
        return "meno di un anno"
    if age == 1:
        return "1 anno"
    return f"{age} anni"


def validate_data_nascita(value):
    check = normalize_date_value(value)
    if check is None:
        return

    today = timezone.localdate()
    if check > today:
        raise forms.ValidationError(NASCITA_FUTURA_MESSAGE)

    age = age_in_years(check, today)
    if age > NASCITA_ETA_LIMITE:
        raise forms.ValidationError(
            NASCITA_TROPPO_VECCHIA_MESSAGE.format(limit=NASCITA_ETA_LIMITE)
        )
    if age > NASCITA_ETA_MAX:
        raise forms.ValidationError(
            NASCITA_OLTRE_MAX_MESSAGE.format(age=age, max_age=NASCITA_ETA_MAX)
        )
    if age < NASCITA_ETA_MIN:
        raise forms.ValidationError(
            NASCITA_SOTTO_MIN_MESSAGE.format(
                age_label=format_age_label(age),
                min_age=NASCITA_ETA_MIN,
            )
        )


def apply_data_nascita_widget(field, *, instance_value=None):
    today = timezone.localdate()
    min_date = shift_years(today, -NASCITA_ETA_LIMITE)
    instance_value = normalize_date_value(instance_value)
    if instance_value and instance_value < min_date:
        min_date = instance_value

    field.widget.attrs["min"] = min_date.isoformat()
    field.widget.attrs["max"] = today.isoformat()
    field.widget.attrs["data-nascita-eta-min"] = str(NASCITA_ETA_MIN)
    field.widget.attrs["data-nascita-eta-max"] = str(NASCITA_ETA_MAX)
    field.widget.attrs["data-nascita-eta-limite"] = str(NASCITA_ETA_LIMITE)


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
