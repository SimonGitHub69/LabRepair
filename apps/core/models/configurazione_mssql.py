from decimal import Decimal

from django.db import models

from apps.core.models.base import BaseModel


class ConfigurazioneMssql(BaseModel):
    attiva = models.BooleanField("Attiva", default=False)
    autenticazione_windows = models.BooleanField(
        "Autenticazione Windows",
        default=False,
        help_text="Usa l'account Windows del processo (Trusted Connection). Non serve utente/password SQL.",
    )
    server = models.CharField("Istanza server", max_length=300, blank=True)
    porta = models.PositiveIntegerField("Porta", default=1433)
    nome_database = models.CharField("Database", max_length=200, blank=True)
    utente = models.CharField("Utente", max_length=200, blank=True)
    password = models.CharField("Password", max_length=200, blank=True)
    prz_pvn_codice = models.CharField(
        "Codice PVN casse",
        max_length=10,
        default="TN",
        blank=True,
        help_text="Valore PRZ_PVN_CODICE su TB_PREZZICASSE (in 4D tipicamente TN).",
    )
    iva_id_cassa = models.PositiveIntegerField(
        "ID IVA casse",
        null=True,
        blank=True,
        help_text="PRZ_IVA_ID (da TabAliquoteIva.ID_IVA_CASSA / CODIVAMETODO).",
    )
    iva_aliquota_cassa = models.DecimalField(
        "Aliquota IVA casse",
        max_digits=5,
        decimal_places=2,
        default=Decimal("22.00"),
        help_text="PRZ_IVA_ALIQUOTA (es. 22.00).",
    )

    class Meta:
        verbose_name = "Configurazione MS-SQL"
        verbose_name_plural = "Configurazioni MS-SQL"

    def __str__(self):
        return "Collegamento MS-SQL"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"attiva": False})
        return obj

    @property
    def is_configured(self):
        base = bool(self.server.strip() and self.nome_database.strip())
        if self.autenticazione_windows:
            return base
        return base and bool(self.utente.strip() and self.password)

    @property
    def server_display(self):
        server = (self.server or "").strip()
        if not server:
            return ""
        if "," in server or "\\" in server:
            return server
        if self.porta:
            return f"{server},{self.porta}"
        return server
