from django.db import models

from apps.core.models.base import BaseModel


class Negozio(BaseModel):
    """Punto vendita / sede operativa LabRepair."""

    codice = models.CharField(
        "Codice",
        max_length=2,
        unique=True,
        help_text="Sigla a 2 caratteri (es. PT, MO, QU).",
    )
    denominazione = models.CharField("Denominazione", max_length=100)
    prefisso_pratica = models.CharField(
        "Prefisso codice riparazione",
        max_length=1,
        help_text="Lettera usata nei codici riparazione (es. P → P26-0001).",
    )
    localita_privacy = models.CharField(
        "Località privacy",
        max_length=100,
        blank=True,
        help_text="Testo località nei documenti privacy (es. PISTOIA).",
    )
    indirizzo = models.CharField("Indirizzo", max_length=255, blank=True)
    civico = models.CharField("Civico", max_length=20, blank=True)
    cap = models.CharField("CAP", max_length=10, blank=True)
    comune = models.CharField("Comune", max_length=100, blank=True)
    provincia = models.CharField("Provincia", max_length=2, blank=True)
    ordine = models.PositiveIntegerField("Ordine", default=0)
    ddt_sezionale = models.CharField(
        "Sezionale DDT",
        max_length=10,
        blank=True,
        default="R",
        help_text="Suffisso numerazione DDT di questo negozio (es. R → 100/R).",
    )
    ddt_numero_iniziale = models.PositiveIntegerField(
        "Numerazione DDT iniziale",
        default=1,
        help_text=(
            "Primo numero DDT per questo negozio. I successivi partono dal massimo "
            "esistente + 1 e non scendono sotto questo valore."
        ),
    )

    class Meta:
        verbose_name = "Negozio"
        verbose_name_plural = "Negozi"
        ordering = ["ordine", "codice"]

    def __str__(self):
        return f"{self.codice} — {self.denominazione}"

    @property
    def sede_operativa(self):
        parts = []
        street = " ".join(part for part in [self.indirizzo, self.civico] if part)
        if street:
            parts.append(street)
        city = " ".join(part for part in [self.cap, self.comune] if part)
        if self.provincia:
            city = f"{city} ({self.provincia})".strip() if city else f"({self.provincia})"
        if city:
            parts.append(city)
        return ", ".join(parts)

    def save(self, *args, **kwargs):
        self.codice = (self.codice or "").strip().upper()
        self.denominazione = (self.denominazione or "").strip()
        self.prefisso_pratica = (self.prefisso_pratica or "").strip().upper()[:1]
        self.localita_privacy = (self.localita_privacy or "").strip()
        self.indirizzo = (self.indirizzo or "").strip()
        self.civico = (self.civico or "").strip()
        self.cap = (self.cap or "").strip()
        self.comune = (self.comune or "").strip()
        self.provincia = (self.provincia or "").strip().upper()[:2]
        self.ddt_sezionale = (self.ddt_sezionale or "").strip().upper() or "R"
        if not self.prefisso_pratica and self.codice:
            self.prefisso_pratica = self.codice[:1]
        super().save(*args, **kwargs)
        try:
            from apps.core.negozi import refresh_negozi_cache

            refresh_negozi_cache()
        except Exception:
            pass

    def soft_delete(self, user=None):
        super().soft_delete(user=user)
        try:
            from apps.core.negozi import refresh_negozi_cache

            refresh_negozi_cache()
        except Exception:
            pass
