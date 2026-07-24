from django import forms

from apps.anagrafiche.models import Indirizzo
from apps.core.widgets import NoAutofillTextInput


class IndirizzoForm(forms.ModelForm):
    class Meta:
        model = Indirizzo
        fields = [
            "tipo",
            "indirizzo",
            "civico",
            "cap",
            "comune",
            "provincia",
            "nazione",
            "principale",
            "note",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "indirizzo": NoAutofillTextInput(),
            "civico": NoAutofillTextInput(),
            "cap": NoAutofillTextInput(),
            "comune": NoAutofillTextInput(),
            "provincia": NoAutofillTextInput(),
            "nazione": NoAutofillTextInput(),
            "principale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["indirizzo"].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault("autocomplete", "off")

    def clean(self):
        cleaned_data = super().clean()
        has_details = any(
            cleaned_data.get(field_name)
            for field_name in [
                "indirizzo",
                "civico",
                "cap",
                "comune",
                "provincia",
                "principale",
                "note",
            ]
        )

        if has_details and not cleaned_data.get("indirizzo"):
            self.add_error("indirizzo", "Inserisci l'indirizzo.")

        return cleaned_data
