from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from apps.core.models import Azienda


def normalize_website_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    URLValidator()(value)
    return value


class AziendaForm(forms.ModelForm):
    sito_web = forms.CharField(
        required=False,
        label="Sito web",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "www.esempio.it",
            }
        ),
    )

    class Meta:
        model = Azienda
        fields = [
            "ragione_sociale",
            "partita_iva",
            "codice_fiscale",
            "email",
            "pec",
            "telefono",
            "sito_web",
            "indirizzo",
            "civico",
            "cap",
            "comune",
            "provincia",
            "logo",
            "note",
        ]
        widgets = {
            "ragione_sociale": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "partita_iva": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "codice_fiscale": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "pec": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "indirizzo": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "civico": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "cap": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "comune": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "provincia": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off", "maxlength": "2"}),
            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".png,.jpg,.jpeg,.webp,.svg",
                }
            ),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def clean_sito_web(self):
        value = self.cleaned_data.get("sito_web", "")
        try:
            return normalize_website_url(value)
        except ValidationError as exc:
            raise forms.ValidationError("Inserisci un indirizzo web valido.") from exc
