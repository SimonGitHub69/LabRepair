from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from apps.core.models import Azienda, Negozio


def normalize_website_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    URLValidator()(value)
    return value


class NegozioForm(forms.ModelForm):
    class Meta:
        model = Negozio
        fields = [
            "codice",
            "denominazione",
            "prefisso_pratica",
            "localita_privacy",
            "indirizzo",
            "civico",
            "cap",
            "comune",
            "provincia",
            "ordine",
            "ddt_sezionale",
            "ddt_numero_iniziale",
            "note",
        ]
        widgets = {
            "codice": forms.TextInput(
                attrs={
                    "class": "form-control text-uppercase",
                    "autocomplete": "off",
                    "maxlength": "2",
                    "style": "max-width: 5rem;",
                }
            ),
            "denominazione": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "prefisso_pratica": forms.TextInput(
                attrs={
                    "class": "form-control text-uppercase",
                    "autocomplete": "off",
                    "maxlength": "1",
                    "style": "max-width: 4rem;",
                }
            ),
            "localita_privacy": forms.TextInput(
                attrs={"class": "form-control text-uppercase", "autocomplete": "off"}
            ),
            "indirizzo": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "civico": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off", "style": "max-width: 6rem;"}
            ),
            "cap": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off", "style": "max-width: 7rem;"}
            ),
            "comune": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "provincia": forms.TextInput(
                attrs={
                    "class": "form-control text-uppercase",
                    "autocomplete": "off",
                    "maxlength": "2",
                    "style": "max-width: 4rem;",
                }
            ),
            "ordine": forms.NumberInput(attrs={"class": "form-control", "min": "0", "style": "max-width: 8rem;"}),
            "ddt_sezionale": forms.TextInput(
                attrs={
                    "class": "form-control text-uppercase",
                    "autocomplete": "off",
                    "style": "max-width: 6rem;",
                }
            ),
            "ddt_numero_iniziale": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "style": "max-width: 10rem;"}
            ),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2, "autocomplete": "off"}),
        }

    def clean_codice(self):
        value = (self.cleaned_data.get("codice") or "").strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValidationError("Il codice deve essere di 2 lettere (es. PT).")
        qs = Negozio.objects.filter(codice=value, is_active=True)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Esiste già un negozio con questo codice.")
        return value

    def clean_prefisso_pratica(self):
        value = (self.cleaned_data.get("prefisso_pratica") or "").strip().upper()
        if not value:
            codice = (
                self.cleaned_data.get("codice") or getattr(self.instance, "codice", "") or ""
            ).strip().upper()
            value = codice[:1]
        if len(value) != 1 or not value.isalpha():
            raise ValidationError("Il prefisso deve essere una lettera.")
        return value

    def clean_provincia(self):
        value = (self.cleaned_data.get("provincia") or "").strip().upper()
        if value and (len(value) != 2 or not value.isalpha()):
            raise ValidationError("La provincia deve essere di 2 lettere (es. PT).")
        return value

    def clean_ddt_sezionale(self):
        return (self.cleaned_data.get("ddt_sezionale") or "").strip().upper() or "R"

    def clean_ddt_numero_iniziale(self):
        value = self.cleaned_data.get("ddt_numero_iniziale")
        try:
            value = int(value or 1)
        except (TypeError, ValueError):
            value = 1
        return max(1, value)


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
