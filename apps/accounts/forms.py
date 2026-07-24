from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.core.negozi import NEGOZI, normalize_negozio_code
from apps.core.pc import (
    detect_client_pc_name,
    get_configurazione_pc,
    negozio_default_for_pc,
)


class LoginForm(AuthenticationForm):
    negozio = forms.ChoiceField(
        label="Negozio",
        choices=NEGOZI,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_negozio"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.detected_nome_pc = ""
        self.detected_pc_config = None
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "off", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "off"}
        )

        if request is not None:
            self.detected_nome_pc = detect_client_pc_name(request)
            self.detected_pc_config = get_configurazione_pc(self.detected_nome_pc)
            if not self.is_bound and self.detected_pc_config:
                negozio = normalize_negozio_code(self.detected_pc_config.negozio_default)
                if negozio:
                    self.fields["negozio"].initial = negozio

    def clean(self):
        cleaned = super().clean()
        negozio = normalize_negozio_code(cleaned.get("negozio"))
        if not negozio and self.detected_pc_config:
            negozio = negozio_default_for_pc(self.detected_pc_config.nome_pc)
            if negozio:
                cleaned["negozio"] = negozio
        cleaned["nome_pc"] = (
            self.detected_pc_config.nome_pc if self.detected_pc_config else ""
        )
        return cleaned
