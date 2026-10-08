from datetime import datetime
from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from apps.core.date_fields import (
    apply_current_year_date_widget,
    apply_current_year_datetime_widget,
    apply_pratica_date_widget,
    validate_current_year_date,
    validate_not_before_today,
    validate_pratica_date,
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
from apps.pratiche.ddt_service import (
    DDT_ASPETTO_DEFAULT,
    DDT_CAUSALE_DEFAULT,
    DDT_TRASPORTO_DEFAULT,
    DDT_VETTORE_DEFAULT,
    buste_aperte_queryset,
    find_busta_aperta_by_codice,
    get_ddt_sezionale_default,
    get_next_ddt_numero,
    parse_busta_codici,
)
from apps.core.programma import get_configurazione_programma

PRATICA_DATE_FIELDS = (
    "data_apertura",
    "data_scadenza",
    "data_riparatore",
    "data_rientro",
    "data_vendita",
)

CLIENTE_BLOCCATO_MSG = (
    "Il cliente non è modificabile dopo la stampa della busta "
    "o se la riparazione è evasa."
)
TESTATA_BLOCCATA_MSG = (
    "I campi di testata non sono modificabili dopo la stampa della busta "
    "o se la riparazione è evasa."
)
TESTATA_BLOCCATA_TITLE = (
    "Testata bloccata: busta stampata oppure riparazione evasa"
)

# Sezione Accettazione: bloccati dopo stampa busta.
PRATICA_TESTATA_FIELDS = (
    "cliente",
    "operatore",
    "referente_cognome",
    "referente_nome",
    "referente_telefono",
    "referente_cellulare",
    "referente_email",
    "data_apertura",
)


def _format_referente_nome(value):
    return " ".join(
        (part[:1].upper() + part[1:].lower()) if part else ""
        for part in (value or "").strip().split()
    )


class OptionalClienteChoiceField(forms.ModelChoiceField):
    """Se l'ID non è nel queryset, non blocca: lascia None e decide clean()."""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return super().to_python(value)
        except forms.ValidationError:
            return None


class PraticaForm(forms.ModelForm):
    cliente = OptionalClienteChoiceField(
        queryset=Anagrafica.objects.none(),
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_cliente"}),
    )
    forza_documento_scaduto = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(attrs={"id": "id_forza_documento_scaduto"}),
    )
    forza_senza_telefono = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(attrs={"id": "id_forza_senza_telefono"}),
    )

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
            "numero_scontrino",
            "senza_spesa",
            "data_vendita",
            "priorita",
        ]
        widgets = {
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
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
            "descrizione": forms.Textarea(
                attrs={"class": "form-control st-autosize", "rows": 2, "data-autosize": "1"}
            ),
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
            "numero_scontrino": forms.TextInput(attrs={"class": "form-control"}),
            "senza_spesa": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_senza_spesa"}),
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
            return str(getattr(initial_cliente, "pk", initial_cliente))

        return ""

    def __init__(self, *args, **kwargs):
        kwargs.pop("operatore_primo", False)
        layout_compatto = bool(kwargs.pop("layout_compatto", False))
        stato_come_radio = bool(kwargs.pop("stato_come_radio", False))
        super().__init__(*args, **kwargs)
        self.stato_come_radio = stato_come_radio
        if layout_compatto:
            self.fields["descrizione"].widget.attrs["rows"] = 2
            self.fields["descrizione"].widget.attrs["class"] = "form-control st-autosize"
            self.fields["descrizione"].widget.attrs["data-autosize"] = "1"
        if stato_come_radio:
            self.fields["stato"].widget = forms.RadioSelect(
                attrs={"class": "form-check-input", "tabindex": "-1"}
            )
        cliente_id = self._resolve_cliente_id()
        # Il ModelChoiceField valida solo sul queryset: se l'ID inviato non c'è
        # (es. cliente soft-deleted ancora sulla pratica) Django risponde
        # «Scegli un'opzione valida» in stampa/salva AJAX.
        if cliente_id:
            selected_qs = Anagrafica.objects.filter(
                pk=cliente_id,
                tipo=Anagrafica.Tipo.CLIENTE,
            ).prefetch_related("contatti", "indirizzi")
            self.fields["cliente"].queryset = selected_qs
            self.selected_cliente = (
                selected_qs.filter(is_active=True).first() or selected_qs.first()
            )
        else:
            self.fields["cliente"].queryset = Anagrafica.objects.none()
            self.selected_cliente = None
        self.selected_cliente_anagrafica = None
        if self.selected_cliente:
            from apps.pratiche.cliente_referente import get_referente_from_cliente

            referente = get_referente_from_cliente(self.selected_cliente)
            self.selected_cliente_anagrafica = referente.get("anagrafica")
        self.fields["cliente"].required = False
        self.fields["cliente"].error_messages.update(
            {
                "required": "Seleziona un cliente oppure inserisci Nome e Cognome.",
                "invalid_choice": (
                    "Il cliente selezionato non è valido. "
                    "Selezionalo di nuovo dalla ricerca oppure inserisci Nome e Cognome."
                ),
            }
        )
        self.cliente_bloccato = bool(
            self.instance.pk and getattr(self.instance, "testata_bloccata", False)
        )
        self.testata_bloccata = self.cliente_bloccato
        # Operatore assente: si può inserire anche a testata bloccata. Se c'è già, resta bloccato.
        self.operatore_inseribile = bool(self.instance.pk and not self.instance.operatore_id)
        if self.testata_bloccata:
            for field_name in PRATICA_TESTATA_FIELDS:
                if field_name == "operatore" and self.operatore_inseribile:
                    continue
                field = self.fields.get(field_name)
                if not field:
                    continue
                # disabled: Django ignora il POST e tiene il valore dell'istanza.
                field.disabled = True
                field.widget.attrs["readonly"] = "readonly"
                field.widget.attrs["aria-disabled"] = "true"
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
        self.fields["referente_telefono"].widget.attrs["placeholder"] = "Telefono o cellulare consigliato"
        self.fields["referente_cellulare"].widget.attrs["placeholder"] = "Telefono o cellulare consigliato"
        self.fields["operatore"].queryset = Operatore.objects.filter(is_active=True)
        self.fields["operatore"].required = True
        self.fields["operatore"].empty_label = "Seleziona operatore"
        self.fields["operatore"].error_messages.update(
            {"required": "Seleziona un operatore."}
        )
        if self.testata_bloccata and self.operatore_inseribile:
            self.fields["operatore"].help_text = (
                "Manca l'operatore: puoi inserirlo anche con la busta già stampata."
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
            {
                "required": "Inserisci il peso quando è indicato il tipo di metallo.",
            }
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
            # Min = oggi solo in creazione: in modifica una data retroattiva è ammissibile.
            min_date = (
                timezone.localdate()
                if field_name == "data_scadenza" and not self.instance.pk
                else None
            )
            apply_pratica_date_widget(
                date_field,
                min_date=min_date,
                instance_value=instance_value,
            )
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
        self.fields["numero_scontrino"].required = False
        self.fields["numero_scontrino"].label = "N. scontrino"
        # readonly (non disabled): il valore resta in POST e non viene azzerato al Salva.
        self.fields["numero_scontrino"].disabled = False
        self.fields["numero_scontrino"].widget.attrs["readonly"] = True
        self.fields["numero_scontrino"].widget.attrs["tabindex"] = "-1"
        self.fields["numero_scontrino"].help_text = "Valorizzato automaticamente dalla cassa."
        self.fields["prezzo_al"].label = "Prezzo al Pubblico"
        self.tipo_oggetto_um_map = {
            str(tipo.pk): tipo.um for tipo in self.fields["tipo_oggetto"].queryset
        }
        self.fields["prezzo_unita"].label = "Prezzo al (gr)"
        self.fields["prezzo_unita"].widget.attrs["data-prezzo-unita-field"] = "true"
        self.fields["oro_aggiunto"].label = "Peso aggiunto (gr)"

        if not self.instance.pk and not self.initial.get("data_apertura"):
            self.initial["data_apertura"] = timezone.localdate()

        # Data apertura automatica: non modificabile dall'utente.
        self.fields["data_apertura"].disabled = True
        self.fields["data_apertura"].help_text = "Impostata automaticamente all'apertura della riparazione."

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
                "numero_scontrino",
                "senza_spesa",
                "data_vendita",
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
            value = cleaned_data.get(field_name)
            if not value:
                continue
            try:
                validate_pratica_date(
                    value,
                    instance=self.instance,
                    field_name=field_name,
                )
            except forms.ValidationError as exc:
                self.add_error(field_name, exc)

        tipologia = cleaned_data.get("tipologia")
        cliente = cleaned_data.get("cliente")
        referente_cognome = (cleaned_data.get("referente_cognome") or "").strip().upper()
        referente_nome = _format_referente_nome(cleaned_data.get("referente_nome"))
        referente_telefono = (cleaned_data.get("referente_telefono") or "").strip()
        referente_cellulare = (cleaned_data.get("referente_cellulare") or "").strip()
        cleaned_data["referente_nome"] = referente_nome
        cleaned_data["referente_cognome"] = referente_cognome
        cleaned_data["referente_telefono"] = referente_telefono
        cleaned_data["referente_cellulare"] = referente_cellulare
        self.documento_scaduto_cliente = None

        if self.testata_bloccata:
            # Valori POST ignorati: ripristina sempre la testata salvata in DB.
            cleaned_data["cliente"] = self.instance.cliente
            cliente = self.instance.cliente
            if self.instance.operatore_id:
                cleaned_data["operatore"] = self.instance.operatore
            cleaned_data["data_apertura"] = self.instance.data_apertura
            cleaned_data["referente_cognome"] = (self.instance.referente_cognome or "").strip().upper()
            cleaned_data["referente_nome"] = _format_referente_nome(self.instance.referente_nome)
            cleaned_data["referente_telefono"] = (self.instance.referente_telefono or "").strip()
            cleaned_data["referente_cellulare"] = (self.instance.referente_cellulare or "").strip()
            cleaned_data["referente_email"] = (self.instance.referente_email or "").strip()
            referente_cognome = cleaned_data["referente_cognome"]
            referente_nome = cleaned_data["referente_nome"]
            referente_telefono = cleaned_data["referente_telefono"]
            referente_cellulare = cleaned_data["referente_cellulare"]
            posted_id = (self.data.get("cliente") or "").strip()
            if posted_id and str(self.instance.cliente_id or "") != posted_id:
                self.add_error("cliente", CLIENTE_BLOCCATO_MSG)

        if not cliente and not (referente_nome and referente_cognome):
            self.add_error(
                "cliente",
                "Seleziona un cliente oppure inserisci Nome e Cognome.",
            )

        if not referente_telefono and not referente_cellulare:
            if not cleaned_data.get("forza_senza_telefono"):
                self.add_error(
                    "referente_telefono",
                    "Inserisci il telefono o il cellulare, oppure conferma «Forza salvataggio».",
                )
                self.add_error(
                    "referente_cellulare",
                    "Inserisci il telefono o il cellulare, oppure conferma «Forza salvataggio».",
                )

        if tipologia == Pratica.Tipologia.PREZIOSO:
            tipo_metallo = (cleaned_data.get("tipo_metallo") or "").strip()
            if tipo_metallo:
                peso = cleaned_data.get("peso_grammi")
                if peso is None or peso <= 0:
                    self.add_error(
                        "peso_grammi",
                        "Inserisci il peso quando è indicato il tipo di metallo.",
                    )

        stato = cleaned_data.get("stato")
        senza_spesa = bool(cleaned_data.get("senza_spesa"))
        if stato == Pratica.Stato.IN_CONSEGNA and not senza_spesa:
            prezzo_al = Decimal(cleaned_data.get("prezzo_al") or 0)
            if prezzo_al <= 0:
                self.add_error(
                    "prezzo_al",
                    "Con stato «In consegna» inserisci un Prezzo al Pubblico oppure seleziona Senza Spesa.",
                )

        if (
            tipologia == Pratica.Tipologia.PREZIOSO
            and cliente
            and not self.instance.pk
            and not cleaned_data.get("forza_documento_scaduto")
        ):
            # Nuova riparazione + prezioso: documento scaduto avvisa, ma si può forzare.
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
                        "Documento di identità scaduto: aggiorna i dati nella sezione "
                        "«Documento di identità» e premi «Salva documento», oppure "
                        "conferma «Forza registrazione» per proseguire comunque."
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
        validate_pratica_date(
            value,
            instance=self.instance,
            field_name="data_scadenza",
        )
        # Retroattiva bloccante solo in Nuova riparazione.
        if not self.instance.pk:
            validate_not_before_today(
                value,
                instance=self.instance,
                field_name="data_scadenza",
            )
        return value

    def save(self, commit=True):
        """Non azzerare valori già in anagrafica/DB (cassa sync, date, campi bloccati)."""
        instance = super().save(commit=False)
        if instance.pk:
            stored = (
                Pratica.objects.filter(pk=instance.pk)
                .only(
                    "data_apertura",
                    "data_scadenza",
                    "data_vendita",
                    "numero_scontrino",
                    "prezzo_pagato",
                    "cliente_id",
                    "operatore_id",
                    "stato",
                    "busta_stampata_il",
                    "referente_cognome",
                    "referente_nome",
                    "referente_telefono",
                    "referente_cellulare",
                    "referente_email",
                )
                .first()
            )
            if stored and stored.testata_bloccata:
                instance.cliente_id = stored.cliente_id
                if stored.operatore_id:
                    instance.operatore_id = stored.operatore_id
                instance.data_apertura = stored.data_apertura
                instance.referente_cognome = stored.referente_cognome
                instance.referente_nome = stored.referente_nome
                instance.referente_telefono = stored.referente_telefono
                instance.referente_cellulare = stored.referente_cellulare
                instance.referente_email = stored.referente_email
            if stored:
                # Campi automatici: sempre la copia DB più aggiornata.
                if stored.data_apertura:
                    instance.data_apertura = stored.data_apertura
                stored_scontrino = (stored.numero_scontrino or "").strip()
                if stored_scontrino:
                    # Sempre il valore DB (readonly + sync cassa può essere più recente).
                    instance.numero_scontrino = stored.numero_scontrino

                stored_pagato = stored.prezzo_pagato or 0
                form_pagato = instance.prezzo_pagato or 0
                if stored_pagato and not form_pagato:
                    instance.prezzo_pagato = stored.prezzo_pagato

                if stored.data_vendita and not instance.data_vendita:
                    instance.data_vendita = stored.data_vendita

                if stored.data_scadenza and not instance.data_scadenza:
                    instance.data_scadenza = stored.data_scadenza

        if commit:
            instance.save()
            self.save_m2m()
            from apps.pratiche.cliente_referente import ensure_cliente_from_referente

            user = getattr(instance, "updated_by", None) or getattr(
                instance, "created_by", None
            )
            ensure_cliente_from_referente(instance, user=user)
        return instance


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
                    "class": "form-control st-autosize",
                    "rows": 2,
                    "data-autosize": "1",
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


class DdtCreateForm(forms.Form):
    centro_assistenza = forms.ModelChoiceField(
        label="Centro assistenza",
        queryset=Anagrafica.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    pratiche = forms.ModelMultipleChoiceField(
        label="Buste aperte",
        queryset=Pratica.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    buste_codici = forms.CharField(
        label="Numeri busta aggiuntivi",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Es. P26-0123, P260045",
                "autocomplete": "off",
            }
        ),
        help_text="Anche buste di altri centri; con o senza trattino; codici separati da virgola o spazio.",
    )
    sezionale = forms.CharField(
        label="Sezionale",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control text-uppercase", "style": "max-width: 6rem;"}),
    )
    data_documento = forms.DateField(
        label="Data documento",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )
    causale = forms.CharField(
        label="Causale",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    aspetto_beni = forms.CharField(
        label="Aspetto beni",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    trasporto_a_cura = forms.CharField(
        label="Trasporto a cura",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    vettore = forms.CharField(
        label="Vettore",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    colli = forms.IntegerField(
        label="Colli",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1", "style": "max-width: 8rem;"}),
    )
    peso_lordo_kg = forms.DecimalField(
        label="Peso lordo (kg)",
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "style": "max-width: 10rem;"}),
    )
    data_inizio_trasporto = forms.DateField(
        label="Data inizio trasporto",
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )
    note = forms.CharField(
        label="Note",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def __init__(self, *args, centri_queryset=None, pratiche_queryset=None, negozio=None, **kwargs):
        self.negozio = negozio
        super().__init__(*args, **kwargs)
        oggi = timezone.localdate()
        cfg = get_configurazione_programma()

        self.fields["centro_assistenza"].queryset = centri_queryset or Anagrafica.objects.filter(
            is_active=True,
            tipo=Anagrafica.Tipo.CENTRO_ASSISTENZA,
        ).order_by("ragione_sociale")
        # Accetta anche buste di altri centri (aggiunte per codice).
        self.fields["pratiche"].queryset = pratiche_queryset or buste_aperte_queryset()

        if not self.is_bound:
            self.fields["sezionale"].initial = get_ddt_sezionale_default(self.negozio)
            self.fields["data_documento"].initial = oggi
            self.fields["data_inizio_trasporto"].initial = oggi
            self.fields["causale"].initial = (cfg.ddt_causale or DDT_CAUSALE_DEFAULT).strip() or DDT_CAUSALE_DEFAULT
            self.fields["aspetto_beni"].initial = (
                (cfg.ddt_aspetto_beni or DDT_ASPETTO_DEFAULT).strip() or DDT_ASPETTO_DEFAULT
            )
            self.fields["trasporto_a_cura"].initial = (
                (cfg.ddt_trasporto_a_cura or DDT_TRASPORTO_DEFAULT).strip() or DDT_TRASPORTO_DEFAULT
            )
            self.fields["vettore"].initial = (cfg.ddt_vettore or DDT_VETTORE_DEFAULT).strip() or DDT_VETTORE_DEFAULT

        numero, sezionale = get_next_ddt_numero(
            (self.data.get("sezionale") if self.is_bound else self.fields["sezionale"].initial)
            or get_ddt_sezionale_default(self.negozio),
            negozio=self.negozio,
        )
        self.numero_previsto = f"{numero}/{sezionale}"

    def clean_sezionale(self):
        value = (self.cleaned_data.get("sezionale") or get_ddt_sezionale_default(self.negozio)).strip().upper()
        if not value:
            raise forms.ValidationError("Indica un sezionale.")
        return value

    def clean(self):
        cleaned = super().clean()
        pratiche = list(cleaned.get("pratiche") or [])
        by_id = {p.pk: p for p in pratiche}
        missing = []
        for code in parse_busta_codici(cleaned.get("buste_codici")):
            pratica = find_busta_aperta_by_codice(code)
            if not pratica:
                missing.append(code)
                continue
            by_id[pratica.pk] = pratica
        if missing:
            raise forms.ValidationError(
                "Buste non trovate o già in DDT / chiuse: " + ", ".join(missing)
            )
        if not by_id:
            raise forms.ValidationError("Seleziona o inserisci almeno una busta aperta.")
        cleaned["pratiche"] = list(by_id.values())
        return cleaned


class DdtUpdateForm(forms.Form):
    data_documento = forms.DateField(
        label="Data documento",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )
    causale = forms.CharField(
        label="Causale",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    aspetto_beni = forms.CharField(
        label="Aspetto beni",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    trasporto_a_cura = forms.CharField(
        label="Trasporto a cura",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    vettore = forms.CharField(
        label="Vettore",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    colli = forms.IntegerField(
        label="Colli",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1", "style": "max-width: 8rem;"}),
    )
    peso_lordo_kg = forms.DecimalField(
        label="Peso lordo (kg)",
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "style": "max-width: 10rem;"}),
    )
    data_inizio_trasporto = forms.DateField(
        label="Data inizio trasporto",
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )
    note = forms.CharField(
        label="Note",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    refresh_destinatario = forms.BooleanField(
        label="Aggiorna destinatario dall'anagrafica",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, ddt=None, **kwargs):
        kwargs.pop("pratiche_queryset", None)
        super().__init__(*args, **kwargs)
        self.ddt = ddt
        if ddt and not self.is_bound:
            self.fields["data_documento"].initial = ddt.data_documento
            self.fields["causale"].initial = ddt.causale
            self.fields["aspetto_beni"].initial = ddt.aspetto_beni
            self.fields["trasporto_a_cura"].initial = ddt.trasporto_a_cura
            self.fields["vettore"].initial = ddt.vettore
            self.fields["colli"].initial = ddt.colli
            self.fields["peso_lordo_kg"].initial = ddt.peso_lordo_kg
            self.fields["data_inizio_trasporto"].initial = ddt.data_inizio_trasporto
            self.fields["note"].initial = ddt.note
