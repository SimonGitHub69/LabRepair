from django.db import models
from django.core.validators import FileExtensionValidator

from apps.core.models import BaseModel


def anagrafica_logo_upload_to(instance, filename):
    return f"anagrafiche/{instance.uuid}/logo/{filename}"


class Anagrafica(BaseModel):
    class Tipo(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        FORNITORE = "fornitore", "Fornitore"
        CENTRO_ASSISTENZA = "centro_assistenza", "Centro Assistenza"

    tipo = models.CharField(
        "Tipo",
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.CLIENTE,
    )

    cognome = models.CharField("Cognome", max_length=100, blank=True)
    nome = models.CharField("Nome", max_length=100, blank=True)

    class Sesso(models.TextChoices):
        M = "M", "M"
        F = "F", "F"

    class TipoDocumento(models.TextChoices):
        CARTA_IDENTITA = "carta_identita", "Carta di Identità"
        PATENTE = "patente", "Patente"
        PASSAPORTO = "passaporto", "Passaporto"

    sesso = models.CharField(
        "Sesso",
        max_length=1,
        choices=Sesso.choices,
        blank=True,
    )
    data_nascita = models.DateField("Data nascita", null=True, blank=True)
    luogo_nascita = models.CharField("Luogo nascita", max_length=100, blank=True)
    provincia_nascita = models.CharField("Prov. nascita", max_length=2, blank=True)

    ragione_sociale = models.CharField(
        "Ragione sociale",
        max_length=200,
    )

    partita_iva = models.CharField(
        "Partita IVA",
        max_length=20,
        blank=True,
    )

    codice_fiscale = models.CharField(
        "Codice Fiscale",
        max_length=20,
        blank=True,
    )

    codice_gestionale = models.CharField(
        "Codice gestionale",
        max_length=7,
        blank=True,
        help_text="Codice cliente sul gestionale (GS_ARTICOLI.CODCLIENTE, 7 caratteri).",
    )

    email = models.EmailField(blank=True)

    telefono = models.CharField(
        max_length=30,
        blank=True,
    )

    cellulare = models.CharField(
        "Cellulare",
        max_length=30,
        blank=True,
    )

    documento_tipo = models.CharField(
        "Tipo documento",
        max_length=50,
        blank=True,
    )
    documento_numero = models.CharField("Numero documento", max_length=50, blank=True)
    documento_rilasciato_da = models.CharField("Rilasciato da", max_length=100, blank=True)
    documento_comune_rilascio = models.CharField("Comune rilascio", max_length=100, blank=True)
    documento_provincia_rilascio = models.CharField("Prov. rilascio", max_length=2, blank=True)
    documento_data_rilascio = models.DateField("Data rilascio", null=True, blank=True)
    documento_data_scadenza = models.DateField("Data scadenza", null=True, blank=True)
    stampa_privacy = models.BooleanField("Stampa privacy", default=False)

    logo = models.FileField(
        "Logo",
        upload_to=anagrafica_logo_upload_to,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["png", "jpg", "jpeg", "webp", "svg"],
            )
        ],
    )

    class Meta:
        verbose_name = "Anagrafica"
        verbose_name_plural = "Anagrafiche"
        ordering = ["cognome", "nome", "ragione_sociale"]
        permissions = [
            ("import_clienti_csv", "Può importare clienti da CSV"),
        ]

    @property
    def display_name(self):
        if self.tipo == self.Tipo.CLIENTE:
            full_name = f"{self.cognome} {self.nome}".strip()
            return full_name or self.ragione_sociale
        return self.ragione_sociale

    @property
    def is_cliente(self):
        return self.tipo == self.Tipo.CLIENTE

    @property
    def documento_tipo_label(self):
        labels = dict(self.TipoDocumento.choices)
        value = (self.documento_tipo or "").strip()
        return labels.get(value, value)

    def save(self, *args, **kwargs):
        if self.tipo == self.Tipo.CLIENTE:
            full_name = f"{self.cognome} {self.nome}".strip()
            if full_name:
                self.ragione_sociale = full_name
        else:
            self.nome = ""
            self.cognome = ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name
