from django import forms

from apps.anagrafiche.models import Contatto
from apps.core.widgets import NoAutofillTextInput


class ContattoForm(forms.ModelForm):
    class Meta:
        model = Contatto
        fields = [
            "tipo",
            "valore",
            "descrizione",
            "principale",
            "note",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "valore": NoAutofillTextInput(),
            "descrizione": NoAutofillTextInput(),
            "principale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["valore"].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault("autocomplete", "off")

    def clean(self):
        cleaned_data = super().clean()
        has_details = any(
            cleaned_data.get(field_name)
            for field_name in ["valore", "descrizione", "principale", "note"]
        )

        if has_details and not cleaned_data.get("valore"):
            self.add_error("valore", "Inserisci il valore del contatto.")

        return cleaned_data
