from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.anagrafiche.forms.contatto import ContattoForm
from apps.anagrafiche.forms.indirizzo import IndirizzoForm
from apps.anagrafiche.name_case import format_cognome, format_nome
from apps.core.widgets import NoAutofillEmailInput, NoAutofillTextInput


class AnagraficaForm(forms.ModelForm):

    class Meta:
        model = Anagrafica
        fields = [
            "tipo",
            "cognome",
            "nome",
            "sesso",
            "data_nascita",
            "luogo_nascita",
            "provincia_nascita",
            "ragione_sociale",
            "partita_iva",
            "codice_fiscale",
            "cellulare",
            "telefono",
            "email",
            "documento_tipo",
            "documento_numero",
            "documento_rilasciato_da",
            "documento_data_rilascio",
            "documento_data_scadenza",
            "stampa_privacy",
            "note",
        ]

        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select", "id": "id_tipo", "autocomplete": "off"}),
            "cognome": NoAutofillTextInput(),
            "nome": NoAutofillTextInput(),
            "sesso": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "data_nascita": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "autocomplete": "off"},
                format="%Y-%m-%d",
            ),
            "luogo_nascita": NoAutofillTextInput(),
            "provincia_nascita": NoAutofillTextInput(
                attrs={"class": "form-control text-uppercase", "maxlength": "2"}
            ),
            "ragione_sociale": NoAutofillTextInput(),
            "partita_iva": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            # TextInput semplice: il widget NoAutofill (hidden+mirror) azzerava il CF in POST.
            "codice_fiscale": forms.TextInput(
                attrs={
                    "class": "form-control text-uppercase",
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
            "cellulare": NoAutofillTextInput(),
            "telefono": NoAutofillTextInput(),
            "email": NoAutofillEmailInput(),
            "documento_tipo": NoAutofillTextInput(),
            "documento_numero": NoAutofillTextInput(),
            "documento_rilasciato_da": NoAutofillTextInput(),
            "documento_data_rilascio": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "autocomplete": "off"},
                format="%Y-%m-%d",
            ),
            "documento_data_scadenza": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "autocomplete": "off"},
                format="%Y-%m-%d",
            ),
            "stampa_privacy": forms.RadioSelect(choices=[(True, "Si"), (False, "No")]),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 4, "autocomplete": "off"}),
        }

    def __init__(self, *args, prezioso=False, **kwargs):
        self.prezioso = prezioso
        super().__init__(*args, **kwargs)
        self.fields["cognome"].required = False
        self.fields["nome"].required = False
        self.fields["ragione_sociale"].required = False
        self.fields["sesso"].choices = [("", "—")] + list(Anagrafica.Sesso.choices)
        for field_name in (
            "data_nascita",
            "documento_data_rilascio",
            "documento_data_scadenza",
        ):
            self.fields[field_name].input_formats = ["%Y-%m-%d"]
        for field in self.fields.values():
            field.widget.attrs.setdefault("autocomplete", "off")

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        documento_tipo = (cleaned_data.get("documento_tipo") or "").strip()
        cleaned_data["documento_tipo"] = documento_tipo
        cognome = format_cognome(cleaned_data.get("cognome"))
        nome = format_nome(cleaned_data.get("nome"))
        cleaned_data["cognome"] = cognome
        cleaned_data["nome"] = nome
        ragione_sociale = (cleaned_data.get("ragione_sociale") or "").strip()
        cleaned_data["codice_fiscale"] = self._first_non_empty_post(
            "codice_fiscale",
            cleaned_data.get("codice_fiscale"),
        ).upper()
        prezioso = self.prezioso

        if tipo == Anagrafica.Tipo.CLIENTE:
            if not cognome:
                self.add_error("cognome", "Inserisci il cognome del cliente.")
            if not nome:
                self.add_error("nome", "Inserisci il nome del cliente.")
            cleaned_data["ragione_sociale"] = f"{cognome} {nome}".strip()

            if prezioso:
                self._validate_prezioso_cliente(cleaned_data)
        else:
            if not ragione_sociale:
                self.add_error("ragione_sociale", "Inserisci la ragione sociale.")
            cleaned_data["nome"] = ""
            cleaned_data["cognome"] = ""

        return cleaned_data

    def _first_non_empty_post(self, field_name, fallback=""):
        """Se il campo è renderizzato più volte, preferisci il primo valore non vuoto."""
        values = []
        if hasattr(self.data, "getlist"):
            values = self.data.getlist(field_name)
        elif self.data is not None:
            values = [self.data.get(field_name)]
        for value in values:
            text = (value or "").strip()
            if text:
                return text
        return (fallback or "").strip()

    def _validate_prezioso_cliente(self, cleaned_data):
        required_fields = {
            "codice_fiscale": "Inserisci il codice fiscale.",
            "data_nascita": "Inserisci la data di nascita.",
            "luogo_nascita": "Inserisci il luogo di nascita.",
            "documento_tipo": "Inserisci il tipo di documento.",
            "documento_numero": "Inserisci il numero del documento.",
            "documento_data_rilascio": "Inserisci la data di rilascio del documento.",
            "documento_data_scadenza": "Inserisci la data di scadenza del documento.",
        }

        for field_name, message in required_fields.items():
            value = cleaned_data.get(field_name)
            if not value:
                self.add_error(field_name, message)

        scadenza = cleaned_data.get("documento_data_scadenza")
        if scadenza and scadenza < timezone.localdate():
            self.add_error(
                "documento_data_scadenza",
                "Il documento di identità risulta scaduto. Inserisci un documento aggiornato.",
            )

        telefono = (cleaned_data.get("telefono") or "").strip()
        cellulare = (cleaned_data.get("cellulare") or "").strip()
        if not telefono and not cellulare:
            self.add_error("telefono", "Inserisci almeno un recapito telefonico.")
            self.add_error("cellulare", "Inserisci almeno un recapito telefonico.")


ContattoFormSet = inlineformset_factory(
    Anagrafica,
    Contatto,
    form=ContattoForm,
    extra=0,
    can_delete=False,
)


IndirizzoFormSet = inlineformset_factory(
    Anagrafica,
    Indirizzo,
    form=IndirizzoForm,
    extra=0,
    can_delete=False,
)


def build_indirizzo_formset(extra=0):
    return inlineformset_factory(
        Anagrafica,
        Indirizzo,
        form=IndirizzoForm,
        extra=extra,
        can_delete=False,
    )
