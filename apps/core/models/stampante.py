from decimal import Decimal

from django.db import models

from apps.core.models.base import BaseModel


class Stampante(BaseModel):
    configurazione_pc = models.ForeignKey(
        "core.ConfigurazionePC",
        on_delete=models.CASCADE,
        related_name="stampanti_collegate",
        verbose_name="Postazione PC",
        null=True,
        blank=True,
    )
    nome = models.CharField(
        "Nome stampante",
        max_length=200,
        db_index=True,
        help_text="Nome Windows della stampante rilevata sul sistema.",
    )
    descrizione = models.CharField(
        "Descrizione",
        max_length=255,
        blank=True,
        help_text="Descrizione libera (es. stampante buste cassa 1).",
    )
    gap_busta_superiore = models.DecimalField(
        "Gap busta superiore",
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Sposta solo la parte A (mm, due decimali). Positivo = più in basso.",
    )
    gap_busta_inferiore = models.DecimalField(
        "Gap busta inferiore",
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Sposta solo la parte B (mm, due decimali). Positivo = più in basso.",
    )
    porta = models.CharField("Porta", max_length=200, blank=True)
    driver = models.CharField("Driver", max_length=200, blank=True)
    predefinita = models.BooleanField("Predefinita di sistema", default=False)
    stampante_buste = models.BooleanField(
        "Stampante buste",
        default=False,
        help_text=(
            "Se attivo, questa stampante viene usata per la stampa buste "
            "di questa postazione (gap e selezione)."
        ),
    )

    class Meta:
        verbose_name = "Stampante"
        verbose_name_plural = "Stampanti"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["configurazione_pc", "nome"],
                name="core_stampante_unique_per_pc",
            ),
        ]

    def __str__(self):
        label = (self.descrizione or "").strip()
        if label:
            return f"{self.nome} ({label})"
        return self.nome

    def save(self, *args, **kwargs):
        self.nome = (self.nome or "").strip()
        self.descrizione = (self.descrizione or "").strip()
        self.porta = (self.porta or "").strip()
        self.driver = (self.driver or "").strip()
        if self.gap_busta_superiore is None:
            self.gap_busta_superiore = Decimal("0.00")
        if self.gap_busta_inferiore is None:
            self.gap_busta_inferiore = Decimal("0.00")
        super().save(*args, **kwargs)
        if self.stampante_buste and self.configurazione_pc_id and self.is_active:
            (
                Stampante.objects.filter(
                    configurazione_pc_id=self.configurazione_pc_id,
                    is_active=True,
                    stampante_buste=True,
                )
                .exclude(pk=self.pk)
                .update(stampante_buste=False)
            )
