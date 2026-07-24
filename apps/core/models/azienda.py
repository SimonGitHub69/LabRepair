from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models.base import BaseModel


def azienda_logo_upload_to(instance, filename):
    return f"aziende/{instance.uuid}/logo/{filename}"


class Azienda(BaseModel):
    ragione_sociale = models.CharField("Ragione sociale", max_length=200)
    partita_iva = models.CharField("Partita IVA", max_length=20, blank=True)
    codice_fiscale = models.CharField("Codice fiscale", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)
    pec = models.EmailField("PEC", blank=True)
    telefono = models.CharField("Telefono", max_length=30, blank=True)
    sito_web = models.URLField("Sito web", blank=True)
    indirizzo = models.CharField("Indirizzo", max_length=255, blank=True)
    civico = models.CharField("Civico", max_length=20, blank=True)
    cap = models.CharField("CAP", max_length=10, blank=True)
    comune = models.CharField("Comune", max_length=100, blank=True)
    provincia = models.CharField("Provincia", max_length=2, blank=True)
    logo = models.FileField(
        "Logo",
        upload_to=azienda_logo_upload_to,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["png", "jpg", "jpeg", "webp", "svg"],
            )
        ],
    )

    class Meta:
        verbose_name = "Azienda"
        verbose_name_plural = "Aziende"
        ordering = ["ragione_sociale"]

    def __str__(self):
        return self.ragione_sociale

    @property
    def indirizzo_completo(self):
        parts = []
        street = " ".join(part for part in [self.indirizzo, self.civico] if part)
        if street:
            parts.append(street)
        city = " ".join(part for part in [self.cap, self.comune, self.provincia] if part)
        if city:
            parts.append(city)
        return ", ".join(parts)
