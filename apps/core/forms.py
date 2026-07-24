from django import forms

from apps.core.models import ConfigurazioneMssql, ConfigurazionePC, ConfigurazioneProgramma


class ConfigurazioneMssqlForm(forms.ModelForm):
    class Meta:
        model = ConfigurazioneMssql
        fields = [
            "attiva",
            "autenticazione_windows",
            "server",
            "porta",
            "nome_database",
            "utente",
            "password",
            "note",
        ]
        widgets = {
            "attiva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "autenticazione_windows": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "server": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                    "placeholder": "HOST\\ISTANZA oppure 192.168.1.10",
                }
            ),
            "porta": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "nome_database": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                    "placeholder": "Nome database",
                }
            ),
            "utente": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "password": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "password",
                    "autocomplete": "off",
                }
            ),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = False
        if self.instance.pk and self.instance.password:
            self.fields["password"].widget.attrs["placeholder"] = "Password salvata: lascia vuoto per mantenerla"

    def clean_password(self):
        password = (self.cleaned_data.get("password") or "").strip()
        if password:
            return password
        if self.instance.pk and self.instance.password:
            return self.instance.password
        return ""

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("attiva"):
            required_fields = {
                "server": "Inserisci l'istanza server.",
                "nome_database": "Inserisci il database.",
            }
            if not cleaned_data.get("autenticazione_windows"):
                required_fields["utente"] = "Inserisci l'utente."
                required_fields["password"] = "Inserisci la password."

            for field_name, message in required_fields.items():
                if field_name == "password":
                    if not cleaned_data.get("autenticazione_windows") and not cleaned_data.get("password"):
                        self.add_error("password", message)
                elif not (cleaned_data.get(field_name) or "").strip():
                    self.add_error(field_name, message)

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            obj.password = password
        elif self.instance.pk and self.instance.password:
            obj.password = self.instance.password
        if commit:
            obj.save()
        return obj


class ConfigurazioneProgrammaForm(forms.ModelForm):
    class Meta:
        model = ConfigurazioneProgramma
        fields = [
            "modalita_accettazione",
            "layout_stile",
            "liste_righe_per_pagina",
            "barcode_iniziale",
            "webcam_tasto_scatto",
            "webcam_tasto_usa_foto",
            "webcam_tasto_nuovo_scatto",
            "comunicazioni_mostra_allegato",
            "comunicazioni_formato_data",
            "mailto_oggetto",
            "mailto_corpo",
            "privacy_testo_dichiarazione",
            "privacy_testo_diritti",
            "note",
        ]
        widgets = {
            "modalita_accettazione": forms.RadioSelect(
                attrs={"class": "form-check-input"},
            ),
            "layout_stile": forms.RadioSelect(
                attrs={"class": "form-check-input"},
            ),
            "liste_righe_per_pagina": forms.Select(attrs={"class": "form-select"}),
            "barcode_iniziale": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "step": "1",
                    "inputmode": "numeric",
                }
            ),
            "webcam_tasto_scatto": forms.Select(attrs={"class": "form-select"}),
            "webcam_tasto_usa_foto": forms.Select(attrs={"class": "form-select"}),
            "webcam_tasto_nuovo_scatto": forms.Select(attrs={"class": "form-select"}),
            "comunicazioni_mostra_allegato": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "comunicazioni_formato_data": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "mailto_oggetto": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Riparazione {codice} - {cliente}",
                }
            ),
            "mailto_corpo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Gentile {nome} {cognome},\n\n"
                        "la informiamo in merito alla riparazione {codice}."
                    ),
                }
            ),
            "privacy_testo_dichiarazione": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Il sottoscritto/a dichiara che gli oggetti sopra indicati NON sono "
                        "di illecita provenienza e di essere in possesso di tutti i diritti "
                        "atti alla riparazione/modifica degli stessi."
                    ),
                }
            ),
            "privacy_testo_diritti": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Per esercitare i diritti previsti all'art. 7 del Codice in materia di "
                        "protezione dei dati personali...\n"
                        "Ragione sociale, indirizzo, telefono, e-mail...\n"
                        "C/A del Responsabile del trattamento dati."
                    ),
                }
            ),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tasti = {
            "webcam_tasto_scatto": cleaned_data.get("webcam_tasto_scatto") or "",
            "webcam_tasto_usa_foto": cleaned_data.get("webcam_tasto_usa_foto") or "",
            "webcam_tasto_nuovo_scatto": cleaned_data.get("webcam_tasto_nuovo_scatto") or "",
        }
        assegnati = [(nome, valore) for nome, valore in tasti.items() if valore]
        valori = [valore for _, valore in assegnati]

        if len(valori) != len(set(valori)):
            duplicati = {valore for valore in valori if valori.count(valore) > 1}
            messaggio = f"Ogni tasto funzione deve essere univoco. Duplicati: {', '.join(sorted(duplicati))}."
            for nome, valore in assegnati:
                if valore in duplicati:
                    self.add_error(nome, messaggio)

        return cleaned_data


class ComandiVoceForm(forms.ModelForm):
    class Meta:
        model = ConfigurazioneProgramma
        fields = [
            "comandi_voce_attivi",
            "comandi_voce_lingua",
        ]
        widgets = {
            "comandi_voce_attivi": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "comandi_voce_lingua": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        from apps.core.voice_commands import (
            VOICE_COMMAND_DEFINITIONS,
            VOICE_DESTINATION_CHOICES,
            normalize_extra_commands,
            phrases_to_text,
            voice_commands_for_form,
        )

        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        stored = getattr(instance, "comandi_voce_mappa", None) if instance else None
        initial_map = voice_commands_for_form(stored)
        self.voice_command_fields = []
        for item in VOICE_COMMAND_DEFINITIONS:
            field_name = f"voce_{item['key']}"
            self.fields[field_name] = forms.CharField(
                label=item["label"],
                required=False,
                initial=initial_map.get(item["key"], phrases_to_text(item["defaults"])),
                help_text=item["hint"],
                widget=forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "placeholder": phrases_to_text(item["defaults"]),
                        "autocomplete": "off",
                    }
                ),
            )
            self.voice_command_fields.append(
                {
                    "name": field_name,
                    "key": item["key"],
                    "label": item["label"],
                    "hint": item["hint"],
                    "field": self[field_name],
                }
            )

        extras = normalize_extra_commands(
            getattr(instance, "comandi_voce_extra", None) if instance else None
        )
        self.voice_extra_rows = extras
        self.voice_destination_choices = VOICE_DESTINATION_CHOICES

    def clean(self):
        from apps.core.voice_commands import (
            VOICE_BUILTIN_DESTINATION_KEYS,
            VOICE_COMMAND_DEFINITIONS,
            normalize_extra_commands,
            parse_voice_phrases,
            sanitize_internal_url,
        )

        cleaned_data = super().clean()

        mappa = {}
        for item in VOICE_COMMAND_DEFINITIONS:
            field_name = f"voce_{item['key']}"
            phrases = parse_voice_phrases(cleaned_data.get(field_name))
            mappa[item["key"]] = phrases or list(item["defaults"])
        cleaned_data["comandi_voce_mappa"] = mappa

        try:
            total = int(self.data.get("voce_extra_TOTAL_FORMS") or 0)
        except (TypeError, ValueError):
            total = 0
        extras = []
        for index in range(max(0, total)):
            prefix = f"voce_extra-{index}-"
            phrases = parse_voice_phrases(self.data.get(f"{prefix}frasi"))
            if not phrases:
                continue
            destinazione = (self.data.get(f"{prefix}destinazione") or "").strip()
            url = sanitize_internal_url(self.data.get(f"{prefix}url"))
            etichetta = " ".join(
                str(self.data.get(f"{prefix}etichetta") or "").split()
            ).strip()
            if destinazione == "url":
                if not url:
                    self.add_error(
                        None,
                        f"Comando personalizzato «{phrases[0]}»: indica un URL interno (es. /pratiche/operatori/).",
                    )
                    continue
            elif destinazione not in VOICE_BUILTIN_DESTINATION_KEYS:
                self.add_error(
                    None,
                    f"Comando personalizzato «{phrases[0]}»: destinazione non valida.",
                )
                continue
            extras.append(
                {
                    "frasi": phrases,
                    "destinazione": destinazione,
                    "url": url if destinazione == "url" else "",
                    "etichetta": etichetta,
                }
            )
        cleaned_data["comandi_voce_extra"] = normalize_extra_commands(extras)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.comandi_voce_mappa = self.cleaned_data.get("comandi_voce_mappa") or {}
        instance.comandi_voce_extra = self.cleaned_data.get("comandi_voce_extra") or []
        if commit:
            instance.save()
        return instance


class ConfigurazionePCForm(forms.ModelForm):
    class Meta:
        model = ConfigurazionePC
        fields = [
            "nome_pc",
            "descrizione",
            "negozio_default",
            "layout_stile",
            "note",
        ]
        widgets = {
            "nome_pc": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                    "placeholder": "Es. DESKTOP-PISTOIA01",
                }
            ),
            "descrizione": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                    "placeholder": "Es. Cassa 1 Pistoia",
                }
            ),
            "negozio_default": forms.Select(attrs={"class": "form-select"}),
            "layout_stile": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, nome_pc_readonly=False, forced_nome_pc="", **kwargs):
        super().__init__(*args, **kwargs)
        self.nome_pc_readonly = bool(nome_pc_readonly)
        self.forced_nome_pc = (forced_nome_pc or "").strip()
        if self.nome_pc_readonly:
            self.fields["nome_pc"].widget.attrs.update(
                {
                    "readonly": True,
                    "class": "form-control-plaintext border rounded px-2 bg-secondary-lt",
                }
            )
            if self.forced_nome_pc:
                self.fields["nome_pc"].initial = self.forced_nome_pc

    def clean_nome_pc(self):
        if self.nome_pc_readonly and self.forced_nome_pc:
            nome = self.forced_nome_pc
        elif self.nome_pc_readonly and self.instance and self.instance.pk:
            nome = (self.instance.nome_pc or "").strip()
        else:
            nome = (self.cleaned_data.get("nome_pc") or "").strip()
        if not nome:
            raise forms.ValidationError("Indicare il nome fisico del PC.")
        qs = ConfigurazionePC.objects.filter(is_active=True, nome_pc__iexact=nome)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Esiste già una postazione con questo nome PC.")
        return nome
