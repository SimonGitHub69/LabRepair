from django import forms


class ImportClientiCsvForm(forms.Form):
    csv_file = forms.FileField(
        label="File CSV",
        help_text="Formato tracciato Pistoia, separatore punto e virgola (;), encoding UTF-8.",
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": ".csv,text/csv",
            }
        ),
    )
    update_existing = forms.BooleanField(
        label="Aggiorna clienti già presenti",
        required=False,
        initial=False,
        help_text="Se attivo, i clienti con lo stesso codice fiscale vengono aggiornati.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    dry_run = forms.BooleanField(
        label="Solo simulazione (dry-run)",
        required=False,
        initial=False,
        help_text="Conta le operazioni senza salvare nulla sul database.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
