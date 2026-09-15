from django.db import models

from apps.core.models.base import BaseModel
from apps.core.models.configurazione_programma import ConfigurazioneProgramma
from apps.core.negozi import NEGOZI


class ConfigurazionePC(BaseModel):
    class PraticaTastoScorciatoia(models.TextChoices):
        DISABILITATO = "", "Disabilitato"
        CTRL_S = "Ctrl+S", "Ctrl+S"
        CTRL_P = "Ctrl+P", "Ctrl+P"
        CTRL_B = "Ctrl+B", "Ctrl+B"
        CTRL_ENTER = "Ctrl+Enter", "Ctrl+Enter"
        CTRL_SHIFT_S = "Ctrl+Shift+S", "Ctrl+Shift+S"
        CTRL_SHIFT_P = "Ctrl+Shift+P", "Ctrl+Shift+P"
        CTRL_SHIFT_B = "Ctrl+Shift+B", "Ctrl+Shift+B"
        ESC = "Esc", "Esc"
        F5 = "F5", "F5"
        F6 = "F6", "F6"
        F7 = "F7", "F7"
        F8 = "F8", "F8"
        F9 = "F9", "F9"
        F10 = "F10", "F10"

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
    layout_alto_contrasto = models.BooleanField(
        "Grafica ad alto contrasto",
        default=False,
        help_text=(
            "Se attivo, in Anagrafiche e Riparazioni aumenta contrasto e dimensione testo "
            "ed evidenzia in blu grassetto i valori inseriti. Non modifica le altre sezioni."
        ),
    )
    stampanti = models.JSONField(
        "Stampanti",
        default=list,
        blank=True,
        help_text="Stampanti Windows associate a questa postazione.",
    )
    busta_stampa_senza_anteprima = models.BooleanField(
        "Stampa busta senza anteprima",
        default=False,
        help_text=(
            "Se attivo, da questa postazione la stampa busta apre subito "
            "la finestra di stampa senza mostrare l'anteprima a schermo."
        ),
    )
    busta_stampa_salva_scheda = models.BooleanField(
        "Salva scheda prima di stampare la busta",
        default=True,
        help_text=(
            "Se attivo, prima di stampare la busta viene salvata la scheda riparazione. "
            "Se disattivo, la busta usa i dati già registrati."
        ),
    )
    busta_stampa_torna_elenco = models.BooleanField(
        "Torna all'elenco dopo la stampa busta",
        default=False,
        help_text=(
            "Se attivo, dopo la stampa busta si torna all'elenco riparazioni. "
            "Se disattivo, si resta nella scheda."
        ),
    )
    pratica_tasto_salva = models.CharField(
        "Tasto Salva",
        max_length=20,
        choices=PraticaTastoScorciatoia.choices,
        blank=True,
        default=PraticaTastoScorciatoia.CTRL_S,
        help_text=(
            "Scorciatoia Salva su tutte le maschere di modifica "
            "(riparazione, anagrafiche, tabelle, parametri)."
        ),
    )
    pratica_tasto_annulla = models.CharField(
        "Tasto Annulla riparazione",
        max_length=20,
        choices=PraticaTastoScorciatoia.choices,
        blank=True,
        default=PraticaTastoScorciatoia.ESC,
        help_text="Scorciatoia per Annulla nella maschera riparazione (stessa in anagrafica cliente).",
    )
    pratica_tasto_stampa_busta = models.CharField(
        "Tasto Stampa busta",
        max_length=20,
        choices=PraticaTastoScorciatoia.choices,
        blank=True,
        default=PraticaTastoScorciatoia.CTRL_P,
        help_text="Scorciatoia per Stampa busta nella maschera riparazione.",
    )
    pratica_tasto_stampa_privacy = models.CharField(
        "Tasto Stampa Privacy",
        max_length=20,
        choices=PraticaTastoScorciatoia.choices,
        blank=True,
        default=PraticaTastoScorciatoia.CTRL_SHIFT_P,
        help_text="Scorciatoia per Stampa Privacy nella maschera riparazione.",
    )
    pratica_tasto_riparatore = models.CharField(
        "Tasto Riparatore",
        max_length=20,
        choices=PraticaTastoScorciatoia.choices,
        blank=True,
        default=PraticaTastoScorciatoia.F6,
        help_text="Scorciatoia per portare il focus sul campo Riparatore.",
    )
    pratica_tasto_tipo_oggetto = models.CharField(
        "Tasto Tipo oggetto",
        max_length=20,
        choices=PraticaTastoScorciatoia.choices,
        blank=True,
        default=PraticaTastoScorciatoia.F7,
        help_text="Scorciatoia per portare il focus sul campo Tipo oggetto.",
    )
    pratica_stato_radio = models.BooleanField(
        "Stato riparazione a radio-bottoni",
        default=False,
        help_text=(
            "Se attivo, nella maschera riparazione lo Stato si seleziona "
            "con radio-bottoni (Accettazione, Riparatore, In consegna, …) "
            "al posto del menu a tendina."
        ),
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
        from apps.core.printers import normalize_stampanti

        self.nome_pc = (self.nome_pc or "").strip()
        self.descrizione = (self.descrizione or "").strip()
        self.stampanti = normalize_stampanti(self.stampanti)
        super().save(*args, **kwargs)

    @property
    def layout_compatto(self):
        return self.layout_stile == ConfigurazioneProgramma.LayoutStile.COMPATTA

    @property
    def stampanti_elenco(self):
        from apps.core.printers import normalize_stampanti

        return normalize_stampanti(self.stampanti)
