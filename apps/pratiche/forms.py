from datetime import datetime
from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from apps.core.date_fields import (
    apply_current_year_date_widget,
    apply_current_year_datetime_widget,
    validate_current_year_date,
)
from apps.core.widgets import NoAutofillEmailInput, NoAutofillTextInput

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.cliente_documento import is_documento_identita_scaduto
from apps.pratiche.riparatori import get_assistenza_riparatore_id, is_assistenza_riparatore
from apps.pratiche.models import (
    CategoriaPratica,
    ComunicazionePratica,
    MacroCategoriaPratica,
    Operatore,
    Pratica,
    PraticaCategoriaAllegato,
    PraticaCategoria,
    PraticaCategoriaFile,
    StudioTecnico,
    TipoOggetto,
)

PRATICA_DATE_FIELDS = (
    "data_apertura",
    "data_scadenza",
    "data_riparatore",
    "data_rientro",
    "data_vendita",
)


class PraticaForm(forms.ModelForm):
    class Meta:
        model = Pratica
        fields = [
            "cliente",
            "referente_cognome",
            "referente_nome",
            "referente_telefono",
            "referente_cellulare",
            "referente_email",
            "operatore",
            "riparatore",
            "centro_assistenza",
            "data_apertura",
            "tipologia",
            "tipo_oggetto",
            "stato",
            "descrizione",
            "peso_grammi",
            "tipo_metallo",
            "data_scadenza",
            "data_riparatore",
            "data_rientro",
            "costo_lavorazione",
            "costo_materiale",
            "oro_aggiunto",
            "prezzo_unita",
            "prezzo_al",
            "prezzo_pagato",
            "senza_spesa",
            "data_vendita",
            "note",
            "priorita",
        ]
        widgets = {
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
            "cliente": forms.HiddenInput(attrs={"id": "id_cliente"}),
            "referente_cognome": NoAutofillTextInput(),
            "referente_nome": NoAutofillTextInput(),
            "referente_telefono": NoAutofillTextInput(),
            "referente_cellulare": NoAutofillTextInput(),
            "referente_email": NoAutofillEmailInput(),
            "tipologia": forms.Select(attrs={"class": "form-select"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "priorita": forms.Select(attrs={"class": "form-select"}),
            "data_apertura": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "data_scadenza": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "data_riparatore": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "data_rientro": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "data_vendita": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "operatore": forms.Select(attrs={"class": "form-select"}),
            "tipo_oggetto": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "peso_grammi": forms.NumberInput(attrs={"class": "form-control", "step": "0.001", "min": "0"}),
            "tipo_metallo": forms.Select(attrs={"class": "form-select"}),
            "riparatore": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "centro_assistenza": forms.Select(attrs={"class": "form-select", "autocomplete": "off"}),
            "costo_lavorazione": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "costo_materiale": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "oro_aggiunto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "prezzo_unita": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "prezzo_al": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "prezzo_pagato": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "senza_spesa": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_senza_spesa"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def _cliente_queryset(self):
        return Anagrafica.objects.filter(
            is_active=True,
            tipo=Anagrafica.Tipo.CLIENTE,
        )

    def _resolve_cliente_id(self):
        if self.is_bound:
            value = (self.data.get("cliente") or "").strip()
            if value:
                return value

        if self.instance.pk and self.instance.cliente_id:
            return str(self.instance.cliente_id)

        initial_cliente = self.initial.get("cliente")
        if initial_cliente:
            return str(initial_cliente)

        return ""

    def __init__(self, *args, **kwargs):
        kwargs.pop("operatore_primo", False)
        layout_compatto = bool(kwargs.pop("layout_compatto", False))
        super().__init__(*args, **kwargs)
        if layout_compatto:
            self.fields["descrizione"].widget.attrs["rows"] = 2
            self.fields["note"].widget.attrs["rows"] = 2
        cliente_id = self._resolve_cliente_id()
        cliente_qs = self._cliente_queryset().prefetch_related("contatti", "indirizzi")
        if cliente_id:
            self.fields["cliente"].queryset = cliente_qs.filter(pk=cliente_id)
            self.selected_cliente = cliente_qs.filter(pk=cliente_id).first()
        else:
            self.fields["cliente"].queryset = cliente_qs.none()
            self.selected_cliente = None
        self.selected_cliente_anagrafica = None
        if self.selected_cliente:
            from apps.pratiche.cliente_referente import get_referente_from_cliente

            referente = get_referente_from_cliente(self.selected_cliente)
            self.selected_cliente_anagrafica = referente.get("anagrafica")
        self.fields["cliente"].required = False
        self.fields["cliente"].error_messages.update(
            {"required": "Seleziona un cliente oppure inserisci Nome e Cognome."}
        )
        for field_name in (
            "referente_cognome",
            "referente_nome",
            "referente_telefono",
            "referente_cellulare",
            "referente_email",
        ):
            self.fields[field_name].required = False
        self.fields["referente_telefono"].label = "Telefono"
        self.fields["referente_cellulare"].label = "Cellulare"
        self.fields["referente_telefono"].widget.attrs["placeholder"] = "Telefono o cellulare obbligatorio"
        self.fields["referente_cellulare"].widget.attrs["placeholder"] = "Telefono o cellulare obbligatorio"
        self.fields["operatore"].queryset = Operatore.objects.filter(is_active=True)
        self.fields["operatore"].required = True
        self.fields["operatore"].empty_label = "Seleziona operatore"
        self.fields["operatore"].error_messages.update(
            {"required": "Seleziona un operatore."}
        )
        self.fields["tipo_oggetto"].queryset = TipoOggetto.objects.filter(is_active=True).order_by("denominazione")
        self.fields["tipo_oggetto"].required = True
        self.fields["tipo_oggetto"].empty_label = "Seleziona tipo oggetto"
        self.fields["tipo_oggetto"].label = "Tipo oggetto"
        self.fields["tipo_oggetto"].error_messages.update(
            {"required": "Seleziona un tipo oggetto."}
        )
        self.fields["descrizione"].required = True
        self.fields["descrizione"].error_messages.update(
            {"required": "Inserisci la descrizione."}
        )
        self.fields["tipo_metallo"].required = False
        self.fields["tipo_metallo"].empty_label = "Seleziona tipo di metallo"
        self.fields["peso_grammi"].required = False
        self.fields["peso_grammi"].error_messages.update(
            {"required": "Inserisci il peso per gli oggetti preziosi."}
        )
        self.fields["riparatore"].queryset = StudioTecnico.objects.filter(is_active=True).order_by("denominazione")
        self.fields["riparatore"].required = False
        self.fields["riparatore"].empty_label = "Seleziona riparatore"
        self.fields["riparatore"].label = "Riparatore"
        assistenza_riparatore_id = get_assistenza_riparatore_id()
        self.fields["riparatore"].widget.attrs["data-assistenza-riparatore-id"] = (
            assistenza_riparatore_id or ""
        )
        self.fields["centro_assistenza"].queryset = Anagrafica.objects.filter(
            is_active=True,
            tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA,
        ).order_by("ragione_sociale")
        self.fields["centro_assistenza"].required = False
        self.fields["centro_assistenza"].empty_label = "Seleziona centro assistenza"
        self.fields["centro_assistenza"].label = "Centro assistenza"
        self.assistenza_riparatore_id = assistenza_riparatore_id
        for field_name in PRATICA_DATE_FIELDS:
            date_field = self.fields[field_name]
            date_field.widget.format = "%Y-%m-%d"
            date_field.input_formats = ["%Y-%m-%d"]
            instance_value = getattr(self.instance, field_name, None) if self.instance.pk else None
            # TEMP: sblocca min=oggi su Data prevista consegna
            min_date = None
            apply_current_year_date_widget(
                date_field,
                min_date=min_date,
                instance_value=instance_value,
            )
        # TEMP: consente qualsiasi data su Data prevista consegna
        self.fields["data_scadenza"].widget.attrs.pop("min", None)
        self.fields["data_scadenza"].widget.attrs.pop("max", None)
        self.fields["data_scadenza"].required = True
        self.fields["data_scadenza"].label = "Data prevista consegna"
        self.fields["data_scadenza"].error_messages.update(
            {
                "required": "Inserisci la data prevista consegna.",
            }
        )
        self.fields["data_riparatore"].required = False
        self.fields["data_rientro"].required = False
        self.fields["data_vendita"].required = False
        self.fields["data_vendita"].label = "Data vendita/evasione"
        self.fields["prezzo_al"].label = "Prezzo al Pubblico"
        self.tipo_oggetto_um_map = {
            str(tipo.pk): tipo.um for tipo in self.fields["tipo_oggetto"].queryset
        }
        self.fields["prezzo_unita"].label = "Prezzo al (gr)"
        self.fields["prezzo_unita"].widget.attrs["data-prezzo-unita-field"] = "true"
        self.fields["oro_aggiunto"].label = "Peso aggiunto (gr)"

        if not self.instance.pk and not self.initial.get("data_apertura"):
            self.initial["data_apertura"] = timezone.localdate()

        if not self.instance.pk:
            self.fields["operatore"].widget.attrs["autofocus"] = "autofocus"

        stati_selezionabili = [
            (stato.value, stato.label) for stato in Pratica.STATI_SELEZIONABILI
        ]
        if self.instance.pk and self.instance.stato:
            valori = {value for value, _label in stati_selezionabili}
            if self.instance.stato not in valori:
                stati_selezionabili.insert(
                    0,
                    (
                        self.instance.stato,
                        dict(Pratica.Stato.choices).get(
                            self.instance.stato, self.instance.stato
                        ),
                    ),
                )
        self.fields["stato"].choices = stati_selezionabili

        self.order_fields(
            [
                "operatore",
                "cliente",
                "referente_cognome",
                "referente_nome",
                "referente_telefono",
                "referente_cellulare",
                "referente_email",
                "riparatore",
                "centro_assistenza",
                "data_apertura",
                "tipologia",
                "tipo_oggetto",
                "descrizione",
                "data_scadenza",
                "peso_grammi",
                "tipo_metallo",
                "stato",
                "priorita",
                "data_riparatore",
                "data_rientro",
                "costo_lavorazione",
                "costo_materiale",
                "oro_aggiunto",
                "prezzo_unita",
                "prezzo_al",
                "prezzo_pagato",
                "senza_spesa",
                "data_vendita",
                "note",
            ]
        )

    def clean(self):
        cleaned_data = super().clean()
        riparatore = cleaned_data.get("riparatore")
        centro_assistenza = cleaned_data.get("centro_assistenza")

        if is_assistenza_riparatore(riparatore):
            if not centro_assistenza:
                self.add_error(
                    "centro_assistenza",
                    "Seleziona un centro assistenza.",
                )
        else:
            cleaned_data["centro_assistenza"] = None

        for field_name in PRATICA_DATE_FIELDS:
            # TEMP: sblocca vincolo anno corrente su Data prevista consegna
            if field_name == "data_scadenza":
                continue
            value = cleaned_data.get(field_name)
            if not value:
                continue
            try:
                validate_current_year_date(
                    value,
                    instance=self.instance,
                    field_name=field_name,
                )
            except forms.ValidationError as exc:
                self.add_error(field_name, exc)

        tipologia = cleaned_data.get("tipologia")
        cliente = cleaned_data.get("cliente")
        referente_cognome = (cleaned_data.get("referente_cognome") or "").strip().upper()
        nome_raw = (cleaned_data.get("referente_nome") or "").strip()
        referente_nome = " ".join(
            (part[:1].upper() + part[1:].lower()) if part else ""
            for part in nome_raw.split()
        )
        referente_telefono = (cleaned_data.get("referente_telefono") or "").strip()
        referente_cellulare = (cleaned_data.get("referente_cellulare") or "").strip()
        cleaned_data["referente_nome"] = referente_nome
        cleaned_data["referente_cognome"] = referente_cognome
        cleaned_data["referente_telefono"] = referente_telefono
        cleaned_data["referente_cellulare"] = referente_cellulare
        self.documento_scaduto_cliente = None

        if not cliente and not (referente_nome and referente_cognome):
            self.add_error(
                "cliente",
                "Seleziona un cliente oppure inserisci Nome e Cognome.",
            )

        if not referente_telefono and not referente_cellulare:
            self.add_error(
                "referente_telefono",
                "Inserisci il telefono o il cellulare.",
            )
            self.add_error(
                "referente_cellulare",
                "Inserisci il telefono o il cellulare.",
            )

        if tipologia == Pratica.Tipologia.PREZIOSO:
            peso = cleaned_data.get("peso_grammi")
            if peso is None or peso <= 0:
                self.add_error(
                    "peso_grammi",
                    "Inserisci il peso per gli oggetti preziosi.",
                )

        stato = cleaned_data.get("stato")
        senza_spesa = bool(cleaned_data.get("senza_spesa"))
        if stato == Pratica.Stato.IN_CONSEGNA and not senza_spesa:
            costo_lavorazione = Decimal(cleaned_data.get("costo_lavorazione") or 0)
            costo_materiale = Decimal(cleaned_data.get("costo_materiale") or 0)
            oro_aggiunto = Decimal(cleaned_data.get("oro_aggiunto") or 0)
            prezzo_unita = Decimal(cleaned_data.get("prezzo_unita") or 0)
            prezzo_al = Decimal(cleaned_data.get("prezzo_al") or 0)
            costo_totale = (
                costo_lavorazione + costo_materiale + (oro_aggiunto * prezzo_unita)
            )
            if costo_totale <= 0:
                self.add_error(
                    "senza_spesa",
                    "Con stato «In consegna» inserisci un Costo totale oppure seleziona Senza Spesa.",
                )
            elif prezzo_al <= 0:
                self.add_error(
                    "prezzo_al",
                    "Inserisci il Prezzo al Pubblico.",
                )

        if tipologia == Pratica.Tipologia.PREZIOSO and cliente:
            # Ricarica i dati aggiornati del cliente (date documento).
            cliente = (
                Anagrafica.objects.filter(pk=cliente.pk, is_active=True)
                .only(
                    "id",
                    "cognome",
                    "nome",
                    "ragione_sociale",
                    "documento_data_scadenza",
                )
                .first()
            )
            if cliente and is_documento_identita_scaduto(cliente):
                self.documento_scaduto_cliente = cliente
                self.add_error(
                    "cliente",
                    (
                        "Documento di identità scaduto: aggiorna l'anagrafica del cliente "
                        "con un documento in corso di validità."
                    ),
                )

        return cleaned_data

    def clean_descrizione(self):
        value = (self.cleaned_data.get("descrizione") or "").strip()
        if not value:
            raise forms.ValidationError("Inserisci la descrizione.")
        return value

    def clean_data_scadenza(self):
        value = self.cleaned_data.get("data_scadenza")
        if not value:
            return value

        # TEMP: sblocca blocco "non antecedente a oggi"
        # if value < timezone.localdate():
        #     unchanged_existing = (
        #         self.instance.pk
        #         and self.instance.data_scadenza == value
        #     )
        #     if not unchanged_existing:
        #         raise forms.ValidationError(
        #             "La data prevista consegna non può essere antecedente a oggi."
        #         )

        return value


class StudioTecnicoForm(forms.ModelForm):
    class Meta:
        model = StudioTecnico
        fields = [
            "denominazione",
            "email",
            "telefono",
            "note",
        ]
        widgets = {
            "denominazione": NoAutofillTextInput(),
            "email": NoAutofillEmailInput(),
            "telefono": NoAutofillTextInput(),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Prefisso univoco: evita che Chrome mescoli i suggerimenti
        # con altri form che usano lo stesso name (es. denominazione).
        kwargs.setdefault("prefix", "riparatore")
        super().__init__(*args, **kwargs)


class OperatoreForm(forms.ModelForm):
    class Meta:
        model = Operatore
        fields = [
            "nominativo",
            "note",
        ]
        widgets = {
            "nominativo": NoAutofillTextInput(),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "operatore")
        super().__init__(*args, **kwargs)


class TipoOggettoForm(forms.ModelForm):
    class Meta:
        model = TipoOggetto
        fields = [
            "denominazione",
            "um",
            "descrizione",
            "note",
        ]
        widgets = {
            "denominazione": NoAutofillTextInput(),
            "um": forms.Select(attrs={"class": "form-select"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["um"].required = True
        self.fields["um"].empty_label = None
        self.fields["um"].label = "UM"
        self.fields["um"].error_messages.update(
            {"required": "Seleziona l'unità di misura (ct o gr)."}
        )


class CategoriaPraticaForm(forms.ModelForm):
    class Meta:
        model = CategoriaPratica
        fields = [
            "denominazione",
            "descrizione",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class MacroCategoriaPraticaForm(forms.ModelForm):
    class Meta:
        model = MacroCategoriaPratica
        fields = [
            "denominazione",
            "descrizione",
            "categorie",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categorie": forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].queryset = CategoriaPratica.objects.filter(is_active=True)
        self.fields["categorie"].required = False
        self.fields["categorie"].help_text = (
            "Seleziona le categorie da creare automaticamente quando colleghi la macro-categoria alla riparazione."
        )


class PraticaMacroCategoriaApplyForm(forms.Form):
    macro_categoria = forms.ModelChoiceField(
        label="Macro-categoria",
        queryset=MacroCategoriaPratica.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["macro_categoria"].queryset = MacroCategoriaPratica.objects.filter(is_active=True)


class PraticaCategoriaForm(forms.ModelForm):
    class Meta:
        model = PraticaCategoria
        fields = [
            "macro_categoria",
            "categoria",
            "origine_template",
            "cartella",
            "versione",
            "note",
        ]
        widgets = {
            "macro_categoria": forms.Select(attrs={"class": "form-select"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "origine_template": forms.HiddenInput(),
            "cartella": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": r"D:\Pratiche\Cliente\Cartella oppure https://...",
                }
            ),
            "versione": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.pratica = kwargs.pop("pratica", None)
        super().__init__(*args, **kwargs)
        self.fields["macro_categoria"].queryset = MacroCategoriaPratica.objects.filter(is_active=True)
        self.fields["macro_categoria"].required = False
        self.fields["categoria"].queryset = CategoriaPratica.objects.filter(is_active=True)
        self.fields["cartella"].help_text = (
            "Inserisci un percorso cartella accessibile dal server locale oppure un link web."
        )
        if self.instance.pk and self.instance.origine_template:
            self.fields["macro_categoria"].widget = forms.HiddenInput()
            self.fields["categoria"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        pratica = self.pratica or getattr(self.instance, "pratica", None)
        macro_categoria = cleaned_data.get("macro_categoria")
        categoria = cleaned_data.get("categoria")
        versione = (cleaned_data.get("versione") or "").strip()

        if not pratica or not categoria:
            return cleaned_data

        queryset = PraticaCategoria.objects.filter(
            pratica=pratica,
            macro_categoria=macro_categoria,
            categoria=categoria,
            versione=versione,
            is_active=True,
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            self.add_error(
                "versione",
                "Questa macro-categoria, categoria e versione sono gia' collegate alla riparazione.",
            )

        cleaned_data["versione"] = versione
        return cleaned_data


class PraticaCategoriaFileUploadForm(forms.Form):
    file = forms.FileField(
        label="File",
        widget=forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"}),
    )
    descrizione = forms.CharField(
        label="Descrizione",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )


class PraticaCategoriaAllegatoUploadForm(forms.ModelForm):
    class Meta:
        model = PraticaCategoriaAllegato
        fields = ["file", "descrizione"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"}),
            "descrizione": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Descrizione del file"}
            ),
        }


class PraticaCategoriaFileDescriptionForm(forms.ModelForm):
    class Meta:
        model = PraticaCategoriaFile
        fields = ["descrizione"]
        widgets = {
            "descrizione": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
        }


class ComunicazionePraticaForm(forms.ModelForm):
    class Meta:
        model = ComunicazionePratica
        fields = ["data_ora", "descrizione", "allegato"]
        widgets = {
            "data_ora": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "descrizione": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descrivi la comunicazione, mittente/destinatario, oggetto o contenuto rilevante",
                }
            ),
            "allegato": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".eml,.msg,.pdf,.txt,.html,.htm,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg",
                }
            ),
        }

    def __init__(self, *args, formato_data=None, **kwargs):
        from apps.core.models import ConfigurazioneProgramma
        from apps.core.programma import get_comunicazioni_formato_data

        super().__init__(*args, **kwargs)
        formato = formato_data or get_comunicazioni_formato_data()

        if formato == ConfigurazioneProgramma.ComunicazioniFormatoData.NASCOSTO:
            self.fields.pop("data_ora", None)
            return

        if formato == ConfigurazioneProgramma.ComunicazioniFormatoData.SOLO_DATA:
            field = self.fields["data_ora"]
            field.label = "Data comunicazione"
            field.widget = forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            )
            field.input_formats = ["%Y-%m-%d"]
            instance_value = self.instance.data_ora if self.instance.pk else None
            apply_current_year_date_widget(field, instance_value=instance_value)
            if self.instance.pk and self.instance.data_ora and "data_ora" not in self.initial:
                self.initial["data_ora"] = timezone.localtime(self.instance.data_ora).date()
            elif not self.instance.pk and not self.initial.get("data_ora"):
                self.initial["data_ora"] = timezone.localdate()
            return

        field = self.fields["data_ora"]
        field.widget.format = "%Y-%m-%dT%H:%M"
        field.input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
        instance_value = self.instance.data_ora if self.instance.pk else None
        apply_current_year_datetime_widget(field, instance_value=instance_value)
        if self.instance.pk and self.instance.data_ora and "data_ora" not in self.initial:
            self.initial["data_ora"] = timezone.localtime(self.instance.data_ora).replace(
                second=0, microsecond=0
            )
        elif not self.instance.pk and not self.initial.get("data_ora"):
            self.initial["data_ora"] = timezone.localtime().replace(second=0, microsecond=0)

    def clean_data_ora(self):
        from apps.core.models import ConfigurazioneProgramma
        from apps.core.programma import get_comunicazioni_formato_data

        value = self.cleaned_data.get("data_ora")
        if value is None:
            return value

        validate_current_year_date(
            value,
            instance=self.instance,
            field_name="data_ora",
        )

        formato = get_comunicazioni_formato_data()
        if formato != ConfigurazioneProgramma.ComunicazioniFormatoData.SOLO_DATA:
            return value

        if hasattr(value, "hour"):
            return value

        now = timezone.localtime()
        return timezone.make_aware(
            datetime.combine(value, now.time()),
            timezone.get_current_timezone(),
        )


class BasePraticaCategoriaInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            macro_categoria = form.cleaned_data.get("macro_categoria")
            categoria = form.cleaned_data.get("categoria")
            versione = (form.cleaned_data.get("versione") or "").strip()

            if not categoria:
                continue

            key = (macro_categoria.pk if macro_categoria else None, categoria.pk, versione)

            if key in seen:
                raise forms.ValidationError(
                    "La stessa macro-categoria, categoria e versione e' presente piu' volte."
                )

            seen.add(key)


PraticaCategoriaFormSet = inlineformset_factory(
    Pratica,
    PraticaCategoria,
    form=PraticaCategoriaForm,
    formset=BasePraticaCategoriaInlineFormSet,
    fields=["macro_categoria", "categoria", "origine_template", "versione", "cartella", "note"],
    extra=1,
    can_delete=True,
)
