from datetime import datetime, time

from django import forms
from django.utils import timezone

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda
from apps.core.date_fields import apply_current_year_datetime_widget, validate_current_year_date
from apps.pratiche.models import Pratica


class EventoAgendaForm(forms.ModelForm):
    data_ora = forms.DateTimeField(
        label="Data ora",
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=[
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ],
    )

    class Meta:
        model = EventoAgenda
        fields = [
            "pratica",
            "titolo",
            "tipo",
            "stato",
            "notifica_email",
            "descrizione",
            "note",
        ]
        widgets = {
            "pratica": forms.Select(attrs={"class": "form-select"}),
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "notifica_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pratica"].queryset = (
            Pratica.objects.filter(is_active=True)
            .exclude(stato=Pratica.Stato.ARCHIVIATA)
            .select_related("cliente")
            .order_by("-data_apertura", "-id")
        )

        if self.instance.pk and self.instance.data_inizio and "data_ora" not in self.initial:
            self.initial["data_ora"] = datetime.combine(
                self.instance.data_inizio,
                self.instance.ora_inizio or time.min,
            )
        elif not self.instance.pk and "data_ora" not in self.initial:
            self.initial["data_ora"] = timezone.localtime().replace(second=0, microsecond=0)

        instance_value = None
        if self.instance.pk and self.instance.data_inizio:
            instance_value = datetime.combine(
                self.instance.data_inizio,
                self.instance.ora_inizio or time.min,
            )
        apply_current_year_datetime_widget(
            self.fields["data_ora"],
            instance_value=instance_value,
        )

        self.order_fields(
            [
                "pratica",
                "titolo",
                "tipo",
                "stato",
                "data_ora",
                "notifica_email",
                "descrizione",
                "note",
            ]
        )

    def clean_data_ora(self):
        value = self.cleaned_data.get("data_ora")
        if value is None:
            return value

        validate_current_year_date(
            value,
            instance=self.instance,
            field_name="data_inizio",
        )
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        data_ora = self.cleaned_data["data_ora"]

        if timezone.is_aware(data_ora):
            data_ora = timezone.localtime(data_ora)

        instance.data_inizio = data_ora.date()
        instance.ora_inizio = data_ora.time()
        instance.data_fine = None
        instance.ora_fine = None

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class ConfigurazioneNotificaEmailForm(forms.ModelForm):
    class Meta:
        model = ConfigurazioneNotificaEmail
        fields = [
            "attiva",
            "host",
            "porta",
            "usa_tls",
            "usa_ssl",
            "username",
            "password",
            "mittente",
            "destinatari_default",
            "giorni_preavviso",
            "note",
        ]
        widgets = {
            "attiva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "host": forms.TextInput(attrs={"class": "form-control", "placeholder": "smtp.dominio.it"}),
            "porta": forms.NumberInput(attrs={"class": "form-control"}),
            "usa_tls": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "usa_ssl": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "password": forms.PasswordInput(attrs={"class": "form-control", "render_value": True}),
            "mittente": forms.EmailInput(attrs={"class": "form-control"}),
            "destinatari_default": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Una email per riga oppure separate da virgola",
                }
            ),
            "giorni_preavviso": forms.NumberInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("usa_tls") and cleaned_data.get("usa_ssl"):
            self.add_error("usa_ssl", "TLS e SSL non possono essere attivi insieme.")

        if cleaned_data.get("attiva"):
            required_fields = ["host", "porta", "mittente"]
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, "Campo obbligatorio se le notifiche sono attive.")

        return cleaned_data
