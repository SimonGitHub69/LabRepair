from django.db import models

from apps.core.models.base import BaseModel
from apps.core.models.configurazione_programma import ConfigurazioneProgramma
from apps.core.negozi import NEGOZI


class ConfigurazionePC(BaseModel):
    nome_pc = models.CharField(
        "Nome PC",
        max_length=100,
        db_index=True,
        help_text="Nome fisico del computer (es. DESKTOP-PISTOIA01).",
    )
    descrizione = models.CharField(
        "Descrizione",
        max_length=200,
        blank=True,
        help_text="Etichetta aggiuntiva per riconoscere la postazione.",
    )
    negozio_default = models.CharField(
        "Negozio predefinito",
        max_length=2,
        choices=NEGOZI,
        help_text="Negozio proposto al login da questo PC.",
    )
    layout_stile = models.CharField(
        "Stile grafica",
        max_length=20,
        choices=ConfigurazioneProgramma.LayoutStile.choices,
        default=ConfigurazioneProgramma.LayoutStile.STANDARD,
        help_text="Interfaccia usata da questa postazione (sovrascrive Parametri programma).",
    )

    class Meta:
        verbose_name = "Configurazione PC"
        verbose_name_plural = "Configurazioni PC"
        ordering = ["nome_pc"]

    def __str__(self):
        label = self.descrizione.strip() if self.descrizione else ""
        if label:
            return f"{self.nome_pc} ({label})"
        return self.nome_pc

    def save(self, *args, **kwargs):
        self.nome_pc = (self.nome_pc or "").strip()
        self.descrizione = (self.descrizione or "").strip()
        super().save(*args, **kwargs)

    @property
    def layout_compatto(self):
        return self.layout_stile == ConfigurazioneProgramma.LayoutStile.COMPATTA
