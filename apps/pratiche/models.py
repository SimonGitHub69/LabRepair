from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.negozi import NEGOZI, normalize_negozio_code
from apps.anagrafiche.models import Anagrafica
from apps.core.models import BaseModel


def pratica_foto_upload_to(instance, filename):
    file_name = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    return f"pratiche/{instance.pratica.uuid}/foto/{file_name}"


class CategoriaPratica(BaseModel):
    denominazione = models.CharField("Denominazione", max_length=200, unique=True)
    descrizione = models.TextField("Descrizione", blank=True)

    class Meta:
        verbose_name = "Categoria riparazione"
        verbose_name_plural = "Categorie riparazioni"
        ordering = ["denominazione"]

    def __str__(self):
        return self.denominazione


class MacroCategoriaPratica(BaseModel):
    denominazione = models.CharField("Denominazione", max_length=200, unique=True)
    descrizione = models.TextField("Descrizione", blank=True)
    categorie = models.ManyToManyField(
        CategoriaPratica,
        related_name="macro_categorie",
        verbose_name="Categorie",
        blank=True,
    )

    class Meta:
        verbose_name = "Macro-categoria riparazione"
        verbose_name_plural = "Macro-categorie riparazioni"
        ordering = ["denominazione"]

    def __str__(self):
        return self.denominazione


class TipoOggetto(BaseModel):
    class UnitaMisura(models.TextChoices):
        CT = "ct", "ct"
        GR = "gr", "gr"

    denominazione = models.CharField("Denominazione", max_length=120, unique=True)
    um = models.CharField(
        "UM",
        max_length=2,
        choices=UnitaMisura.choices,
    )
    descrizione = models.TextField("Descrizione", blank=True)

    class Meta:
        verbose_name = "Tipo oggetto"
        verbose_name_plural = "Tipi di oggetto"
        ordering = ["denominazione"]

    def __str__(self):
        return self.denominazione


class Pratica(BaseModel):
    class Stato(models.TextChoices):
        ACCETTAZIONE = "accettazione", "Accettazione"
        RIPARATORE = "riparatore", "Riparatore"
        IN_CONSEGNA = "in_consegna", "In consegna"
        EVASA = "evasa", "Evasa"
        NON_RITIRATA = "non_ritirata", "Non ritirata"
        ANNULLATA = "annullata", "Annullata"
        ARCHIVIATA = "archiviata", "Archiviata"
        BOZZA = "bozza", "Bozza"
        APERTA = "aperta", "Aperta"
        IN_LAVORAZIONE = "in_lavorazione", "In lavorazione"
        IN_ATTESA_CLIENTE = "in_attesa_cliente", "In attesa cliente"
        IN_ATTESA_ESTERNA = "in_attesa_esterna", "In attesa esterna"
        COMPLETATA = "completata", "Completata"

    STATI_SELEZIONABILI = (
        Stato.ACCETTAZIONE,
        Stato.RIPARATORE,
        Stato.IN_CONSEGNA,
        Stato.EVASA,
        Stato.NON_RITIRATA,
        Stato.ANNULLATA,
    )

    class Priorita(models.TextChoices):
        BASSA = "bassa", "Bassa"
        NORMALE = "normale", "Normale"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    class Tipologia(models.TextChoices):
        PREZIOSO = "prezioso", "Prezioso"
        NON_PREZIOSO = "non_prezioso", "Non prezioso"

    class TipoMetallo(models.TextChoices):
        ORO = "oro", "Oro"
        ARGENTO = "argento", "Argento"
        PLATINO = "platino", "Platino"

    codice = models.CharField("Codice", max_length=30, unique=True, blank=True)
    titolo = models.CharField("Oggetto / titolo scheda", max_length=200, blank=True)
    cliente = models.ForeignKey(
        Anagrafica,
        on_delete=models.PROTECT,
        related_name="pratiche",
        verbose_name="Cliente",
        limit_choices_to={"tipo": Anagrafica.Tipo.CLIENTE, "is_active": True},
        null=True,
        blank=True,
    )
    referente_cognome = models.CharField("Cognome", max_length=100, blank=True)
    referente_nome = models.CharField("Nome", max_length=100, blank=True)
    referente_telefono = models.CharField("Telefono", max_length=30, blank=True)
    referente_cellulare = models.CharField("Cellulare", max_length=30, blank=True)
    referente_email = models.EmailField("Email", blank=True)
    negozio = models.CharField(
        "Negozio",
        max_length=2,
        choices=NEGOZI,
        blank=True,
    )
    tipologia = models.CharField(
        "Tipologia oggetto",
        max_length=30,
        choices=Tipologia.choices,
        default=Tipologia.NON_PREZIOSO,
    )
    tipo_oggetto = models.ForeignKey(
        TipoOggetto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pratiche",
        verbose_name="Tipo oggetto",
    )
    stato = models.CharField(
        "Stato",
        max_length=30,
        choices=Stato.choices,
        default=Stato.ACCETTAZIONE,
    )
    priorita = models.CharField(
        "Priorita",
        max_length=20,
        choices=Priorita.choices,
        default=Priorita.NORMALE,
    )
    data_apertura = models.DateField("Data apertura", default=timezone.localdate)
    data_scadenza = models.DateField("Data prevista consegna", null=True, blank=True)
    data_chiusura = models.DateField("Data chiusura", null=True, blank=True)
    data_riparatore = models.DateField("Data riparatore", null=True, blank=True)
    data_rientro = models.DateField("Data rientro", null=True, blank=True)
    data_vendita = models.DateField("Data vendita/evasione", null=True, blank=True)
    responsabile = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pratiche_assegnate",
        verbose_name="Responsabile accesso",
    )
    operatore = models.ForeignKey(
        "Operatore",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="riparazioni",
        verbose_name="Operatore",
    )
    descrizione = models.TextField("Descrizione", blank=True)
    peso_grammi = models.DecimalField("Peso (gr)", max_digits=10, decimal_places=3, default=0)
    tipo_metallo = models.CharField(
        "Tipo di metallo",
        max_length=20,
        choices=TipoMetallo.choices,
        blank=True,
    )
    riparatore = models.ForeignKey(
        "StudioTecnico",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pratiche_riparazione",
        verbose_name="Riparatore",
    )
    centro_assistenza = models.ForeignKey(
        Anagrafica,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pratiche_centro_assistenza",
        verbose_name="Centro assistenza",
        limit_choices_to={"tipo": Anagrafica.Tipo.CENTRO_ASSISTENZA, "is_active": True},
    )
    costo_lavorazione = models.DecimalField("Costo lavorazione (EUR)", max_digits=10, decimal_places=2, default=0)
    costo_materiale = models.DecimalField("Costo materiale (EUR)", max_digits=10, decimal_places=2, default=0)
    oro_aggiunto = models.DecimalField("Peso aggiunto", max_digits=10, decimal_places=2, default=0)
    prezzo_unita = models.DecimalField("Prezzo al", max_digits=10, decimal_places=2, default=0)
    prezzo_al = models.DecimalField("Prezzo al Pubblico", max_digits=10, decimal_places=2, default=0)
    prezzo_pagato = models.DecimalField("Prezzo pagato", max_digits=10, decimal_places=2, default=0)
    senza_spesa = models.BooleanField(
        "Senza spesa",
        default=False,
        help_text="Se attivo, consente stato In consegna anche con Costo totale a zero.",
    )
    gs_barcode = models.DecimalField(
        "Barcode GS",
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        unique=True,
        help_text="Barcode assegnato in GS_ARTICOLI sul gestionale SQL.",
    )

    class Meta:
        verbose_name = "Riparazione"
        verbose_name_plural = "Riparazioni"
        ordering = ["-data_apertura", "-id"]

    def __str__(self):
        return f"{self.codice} - {self.titolo}" if self.codice else self.titolo

    @property
    def costo_metallo_aggiunto(self):
        return Decimal(self.oro_aggiunto or 0) * Decimal(self.prezzo_unita or 0)

    @property
    def costo_totale(self):
        return (
            Decimal(self.costo_lavorazione or 0)
            + Decimal(self.costo_materiale or 0)
            + self.costo_metallo_aggiunto
        )

    @property
    def peso_aggiunto_label(self):
        um = TipoOggetto.UnitaMisura.GR
        if self.tipo_oggetto_id and self.tipo_oggetto.um:
            um = self.tipo_oggetto.um
        return f"Peso aggiunto ({um})"

    @property
    def prezzo_unita_label(self):
        um = TipoOggetto.UnitaMisura.GR
        if self.tipo_oggetto_id and self.tipo_oggetto.um:
            um = self.tipo_oggetto.um
        return f"Prezzo al ({um})"

    @property
    def is_finale(self):
        return self.stato in {
            self.Stato.COMPLETATA,
            self.Stato.EVASA,
            self.Stato.ANNULLATA,
            self.Stato.ARCHIVIATA,
        }

    @property
    def is_scaduta(self):
        return bool(self.data_scadenza and self.data_scadenza < timezone.localdate() and not self.is_finale)

    @property
    def riparatore_display(self):
        from apps.pratiche.riparatori import is_assistenza_riparatore

        if is_assistenza_riparatore(self.riparatore) and self.centro_assistenza_id:
            return f"ASSISTENZA · {self.centro_assistenza.ragione_sociale}"
        if self.riparatore_id:
            return str(self.riparatore)
        return ""

    @property
    def cliente_label(self):
        if self.cliente_id:
            return self.cliente.display_name
        referente = f"{self.referente_cognome} {self.referente_nome}".strip()
        return referente or "Cliente non indicato"

    def save(self, *args, **kwargs):
        if not self.codice:
            from apps.pratiche.codice import get_next_pratica_codice

            self.codice = get_next_pratica_codice(self.negozio)
            if not self.codice:
                raise ValueError("Impossibile generare il codice riparazione senza negozio valido.")
            self.negozio = normalize_negozio_code(self.negozio)

        if not self.titolo:
            tipo_label = self.tipo_oggetto.denominazione if self.tipo_oggetto_id else ""
            self.titolo = tipo_label or f"Riparazione {self.codice}"

        if self.stato in {self.Stato.EVASA, self.Stato.COMPLETATA, self.Stato.ANNULLATA} and not self.data_chiusura:
            self.data_chiusura = timezone.localdate()

        super().save(*args, **kwargs)


class PraticaFoto(BaseModel):
    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.CASCADE,
        related_name="foto",
        verbose_name="Riparazione",
    )
    immagine = models.FileField(
        "Immagine",
        upload_to=pratica_foto_upload_to,
        max_length=500,
    )
    didascalia = models.CharField("Didascalia", max_length=200, blank=True)

    class Meta:
        verbose_name = "Foto riparazione"
        verbose_name_plural = "Foto riparazioni"
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.file_nome or f"Foto {self.pk}"

    @property
    def file_nome(self):
        if not self.immagine:
            return ""

        return self.immagine.name.rsplit("/", 1)[-1]


class TemplatePratica(BaseModel):
    tipologia = models.CharField(
        "Tipologia",
        max_length=30,
        choices=Pratica.Tipologia.choices,
        unique=True,
    )
    macro_categorie = models.ManyToManyField(
        MacroCategoriaPratica,
        related_name="template_pratiche",
        verbose_name="Macro-categorie",
        blank=True,
    )
    categorie = models.ManyToManyField(
        CategoriaPratica,
        related_name="template_pratiche",
        verbose_name="Categorie singole",
        blank=True,
    )

    class Meta:
        verbose_name = "Template riparazione"
        verbose_name_plural = "Template riparazioni"
        ordering = ["tipologia"]

    def __str__(self):
        return self.get_tipologia_display()


class PraticaCategoria(BaseModel):
    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.CASCADE,
        related_name="categoria_collegamenti",
        verbose_name="Riparazione",
    )
    categoria = models.ForeignKey(
        CategoriaPratica,
        on_delete=models.PROTECT,
        related_name="pratica_collegamenti",
        verbose_name="Categoria",
    )
    macro_categoria = models.ForeignKey(
        MacroCategoriaPratica,
        on_delete=models.PROTECT,
        related_name="categoria_collegamenti",
        verbose_name="Macro-categoria",
        null=True,
        blank=True,
    )
    cartella = models.CharField("Cartella", max_length=500, blank=True)
    versione = models.CharField("Versione", max_length=50, blank=True)
    origine_template = models.BooleanField("Origine template", default=False)

    class Meta:
        verbose_name = "Categoria riparazione collegata"
        verbose_name_plural = "Categorie riparazione collegate"
        ordering = ["macro_categoria__denominazione", "categoria__denominazione", "versione"]
        constraints = [
            models.UniqueConstraint(
                fields=["pratica", "categoria", "versione"],
                condition=models.Q(is_active=True, macro_categoria__isnull=True),
                name="unique_pratica_categoria_versione_senza_macro",
            ),
            models.UniqueConstraint(
                fields=["pratica", "macro_categoria", "categoria", "versione"],
                condition=models.Q(is_active=True, macro_categoria__isnull=False),
                name="unique_pratica_macro_categoria_categoria_versione",
            ),
        ]

    def __str__(self):
        label = str(self.categoria)
        if self.macro_categoria:
            label = f"{self.macro_categoria} / {label}"
        if self.versione:
            label = f"{label} - {self.versione}"
        return label


class PraticaMacroCategoria(BaseModel):
    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.CASCADE,
        related_name="macro_categoria_collegamenti",
        verbose_name="Riparazione",
    )
    macro_categoria = models.ForeignKey(
        MacroCategoriaPratica,
        on_delete=models.PROTECT,
        related_name="pratica_collegamenti",
        verbose_name="Macro-categoria",
    )

    class Meta:
        verbose_name = "Macro-categoria riparazione collegata"
        verbose_name_plural = "Macro-categorie riparazione collegate"
        ordering = ["macro_categoria__denominazione"]
        constraints = [
            models.UniqueConstraint(
                fields=["pratica", "macro_categoria"],
                condition=models.Q(is_active=True),
                name="unique_pratica_macro_categoria_attiva",
            )
        ]

    def __str__(self):
        return f"{self.pratica} - {self.macro_categoria}"


class PraticaCategoriaFile(BaseModel):
    pratica_categoria = models.ForeignKey(
        PraticaCategoria,
        on_delete=models.CASCADE,
        related_name="file_metadati",
        verbose_name="Categoria riparazione",
    )
    percorso_relativo = models.CharField("Percorso relativo", max_length=500)
    descrizione = models.TextField("Descrizione", blank=True)
    scollegato = models.BooleanField("Scollegato dalla riparazione", default=False)

    class Meta:
        verbose_name = "File categoria riparazione"
        verbose_name_plural = "File categorie riparazione"
        ordering = ["percorso_relativo"]
        constraints = [
            models.UniqueConstraint(
                fields=["pratica_categoria", "percorso_relativo"],
                condition=models.Q(is_active=True),
                name="unique_file_categoria_pratica_attivo",
            )
        ]

    def __str__(self):
        return self.percorso_relativo


def pratica_categoria_allegato_upload_to(instance, filename):
    pratica_uuid = instance.pratica_categoria.pratica.uuid
    categoria_uuid = instance.pratica_categoria.uuid
    file_name = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    return f"pratiche/{pratica_uuid}/categorie/{categoria_uuid}/allegati/{file_name}"


class PraticaCategoriaAllegato(BaseModel):
    pratica_categoria = models.ForeignKey(
        PraticaCategoria,
        on_delete=models.CASCADE,
        related_name="allegati_singoli",
        verbose_name="Categoria riparazione",
    )
    file = models.FileField("File", upload_to=pratica_categoria_allegato_upload_to, max_length=500)
    descrizione = models.TextField("Descrizione", blank=True)

    class Meta:
        verbose_name = "Allegato singolo categoria riparazione"
        verbose_name_plural = "Allegati singoli categorie riparazione"
        ordering = ["file"]

    def __str__(self):
        return self.file_nome

    @property
    def file_nome(self):
        if not self.file:
            return ""

        return self.file.name.rsplit("/", 1)[-1]


def comunicazione_upload_to(instance, filename):
    file_name = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    return f"pratiche/{instance.pratica.uuid}/comunicazioni/{file_name}"


class ComunicazionePratica(BaseModel):
    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.CASCADE,
        related_name="comunicazioni",
        verbose_name="Riparazione",
    )
    data_ora = models.DateTimeField("Data e ora comunicazione", default=timezone.now)
    descrizione = models.TextField("Descrizione")
    allegato = models.FileField("File comunicazione", upload_to=comunicazione_upload_to, blank=True, max_length=500)

    class Meta:
        verbose_name = "Comunicazione riparazione"
        verbose_name_plural = "Comunicazioni riparazione"
        ordering = ["-data_ora", "-id"]

    def __str__(self):
        return f"{self.pratica} - {self.data_ora:%d/%m/%Y %H:%M}"

    @property
    def allegato_nome(self):
        if not self.allegato:
            return ""

        return self.allegato.name.rsplit("/", 1)[-1]


class StudioTecnico(BaseModel):
    denominazione = models.CharField("Denominazione", max_length=200, unique=True)
    email = models.EmailField("Email", blank=True)
    telefono = models.CharField("Telefono", max_length=30, blank=True)

    class Meta:
        verbose_name = "Riparatore"
        verbose_name_plural = "Riparatori"
        ordering = ["denominazione"]

    def __str__(self):
        return self.denominazione


class IncaricoTecnico(BaseModel):
    denominazione = models.CharField("Denominazione", max_length=150, unique=True)
    descrizione = models.TextField("Descrizione", blank=True)

    class Meta:
        verbose_name = "Incarico"
        verbose_name_plural = "Incarichi"
        ordering = ["denominazione"]

    def __str__(self):
        return self.denominazione


class Operatore(BaseModel):
    nominativo = models.CharField("Nominativo", max_length=150, unique=True)

    class Meta:
        verbose_name = "Operatore"
        verbose_name_plural = "Operatori"
        ordering = ["nominativo"]

    def __str__(self):
        return self.nominativo


class Tecnico(BaseModel):
    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.CASCADE,
        related_name="tecnici",
        verbose_name="Riparazione",
    )
    nome = models.CharField("Nome", max_length=100)
    cognome = models.CharField("Cognome", max_length=100)
    studio_appartenenza = models.ForeignKey(
        StudioTecnico,
        on_delete=models.PROTECT,
        related_name="tecnici",
        verbose_name="Studio di appartenenza",
        null=True,
        blank=True,
    )
    incarico = models.ForeignKey(
        IncaricoTecnico,
        on_delete=models.PROTECT,
        related_name="tecnici",
        verbose_name="Incarico",
        null=True,
        blank=True,
    )
    email = models.EmailField("Email", blank=True)
    telefono = models.CharField("Telefono", max_length=30, blank=True)

    class Meta:
        verbose_name = "Tecnico"
        verbose_name_plural = "Tecnici"
        ordering = ["cognome", "nome"]

    def __str__(self):
        return f"{self.nome} {self.cognome}".strip()
