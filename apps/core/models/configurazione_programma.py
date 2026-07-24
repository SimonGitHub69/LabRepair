from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models.base import BaseModel

GS_BARCODE_DEFAULT = 500000
GS_BARCODE_MAX_EXCLUSIVE = 90000000


class ConfigurazioneProgramma(BaseModel):
    class ModalitaAccettazione(models.TextChoices):
        STANDARD = "standard", "Standard (cliente per primo)"
        OPERATORE_PRIMA = "operatore_prima", "Operatore per primo"

    class LayoutStile(models.TextChoices):
        STANDARD = "standard", "Grafica standard"
        COMPATTA = "compatta", "Grafica compatta"

    class WebcamTastoFunzione(models.TextChoices):
        DISABILITATO = "", "Disabilitato"
        F1 = "F1", "F1"
        F2 = "F2", "F2"
        F3 = "F3", "F3"
        F4 = "F4", "F4"
        F5 = "F5", "F5"
        F6 = "F6", "F6"
        F7 = "F7", "F7"
        F8 = "F8", "F8"
        F9 = "F9", "F9"
        F10 = "F10", "F10"
        F11 = "F11", "F11"
        F12 = "F12", "F12"

    WebcamTastoScatto = WebcamTastoFunzione

    modalita_accettazione = models.CharField(
        "Modalità accettazione riparazione",
        max_length=30,
        choices=ModalitaAccettazione.choices,
        default=ModalitaAccettazione.STANDARD,
        help_text=(
            "Standard: il form Nuova riparazione inizia dal cliente. "
            "Operatore per primo: il primo campo è l'operatore."
        ),
    )
    layout_stile = models.CharField(
        "Stile grafica maschere",
        max_length=20,
        choices=LayoutStile.choices,
        default=LayoutStile.STANDARD,
        help_text=(
            "Standard: layout arioso. "
            "Compatta: stesse informazioni con meno spazi su Riparazioni e Anagrafiche."
        ),
    )

    class ListeRighePerPagina(models.IntegerChoices):
        DIECI = 10, "10"
        VENTI = 20, "20"
        CINQUANTA = 50, "50"
        CENTO = 100, "100"

    liste_righe_per_pagina = models.PositiveSmallIntegerField(
        "Righe per pagina nelle liste",
        choices=ListeRighePerPagina.choices,
        default=ListeRighePerPagina.VENTI,
        help_text="Numero predefinito di righe nelle liste (modificabile anche dalla barra di paginazione).",
    )
    comandi_voce_attivi = models.BooleanField(
        "Abilita comandi vocali",
        default=False,
        help_text=(
            "Mostra il microfono in barra e permette navigazione/paginazione a voce "
            "(richiede Chrome/Edge e permesso microfono)."
        ),
    )

    class ComandiVoceLingua(models.TextChoices):
        IT_IT = "it-IT", "Italiano"
        EN_US = "en-US", "English (US)"

    comandi_voce_lingua = models.CharField(
        "Lingua riconoscimento vocale",
        max_length=10,
        choices=ComandiVoceLingua.choices,
        default=ComandiVoceLingua.IT_IT,
        help_text="Lingua usata dal riconoscimento vocale del browser.",
    )
    comandi_voce_mappa = models.JSONField(
        "Mappa frasi comandi vocali",
        default=dict,
        blank=True,
        help_text=(
            "Frasi personalizzate per azione. Se vuoto per un'azione, si usano i predefiniti."
        ),
    )
    comandi_voce_extra = models.JSONField(
        "Comandi vocali personalizzati",
        default=list,
        blank=True,
        help_text="Comandi aggiuntivi definiti dall'utente (frasi → destinazione).",
    )
    barcode_iniziale = models.PositiveIntegerField(
        "Numerazione barcode iniziale",
        default=GS_BARCODE_DEFAULT,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(GS_BARCODE_MAX_EXCLUSIVE - 1),
        ],
        help_text=(
            "Primo numero barcode GS assegnato alle riparazioni. "
            "I successivi partono dal massimo esistente + 1 in questa fascia."
        ),
    )
    webcam_tasto_scatto = models.CharField(
        "Tasto scatto foto",
        max_length=3,
        choices=WebcamTastoFunzione.choices,
        blank=True,
        default=WebcamTastoFunzione.DISABILITATO,
        help_text="Apre la webcam oppure scatta una foto con il modale già aperto.",
    )
    webcam_tasto_usa_foto = models.CharField(
        "Tasto usa foto",
        max_length=3,
        choices=WebcamTastoFunzione.choices,
        blank=True,
        default=WebcamTastoFunzione.DISABILITATO,
        help_text="Conferma e usa la foto appena scattata.",
    )
    webcam_tasto_nuovo_scatto = models.CharField(
        "Tasto nuovo scatto",
        max_length=3,
        choices=WebcamTastoFunzione.choices,
        blank=True,
        default=WebcamTastoFunzione.DISABILITATO,
        help_text="Scarta l'anteprima e prepara un nuovo scatto.",
    )
    comunicazioni_mostra_allegato = models.BooleanField(
        "Mostra mail o allegato nelle comunicazioni",
        default=True,
        help_text="Se disattivato, nasconde il campo file/webcam nel form comunicazioni.",
    )

    class ComunicazioniFormatoData(models.TextChoices):
        DATA_ORA = "data_ora", "Data e ora"
        SOLO_DATA = "solo_data", "Solo data"
        NASCOSTO = "nascosto", "Non mostrare (usa data/ora corrente)"

    comunicazioni_formato_data = models.CharField(
        "Campo data comunicazioni",
        max_length=20,
        choices=ComunicazioniFormatoData.choices,
        default=ComunicazioniFormatoData.DATA_ORA,
        help_text="Formato del campo data nel form comunicazioni della scheda riparazione.",
    )
    privacy_testo_diritti = models.TextField(
        "Testo diritti privacy",
        blank=True,
        help_text=(
            "Testo in calce alla scheda Privacy per l'esercizio dei diritti GDPR (art. 7). "
            "Se vuoto, viene generato automaticamente dai dati azienda."
        ),
    )
    privacy_testo_dichiarazione = models.TextField(
        "Testo dichiarazione provenienza",
        blank=True,
        help_text=(
            "Dichiarazione del sottoscritto sulla provenienza e sui diritti degli oggetti "
            "nella scheda Privacy. Se vuoto, viene usato il testo predefinito."
        ),
    )
    mailto_oggetto = models.CharField(
        "Oggetto della mail",
        max_length=200,
        blank=True,
        default="Riparazione {codice} - {cliente}",
        help_text=(
            "Oggetto precompilato quando si apre il client di posta dai filtri "
            "Non ritirate / Ritardo lavorazione. "
            "Segnaposto: {codice}, {cliente}, {nome}, {cognome}."
        ),
    )
    mailto_corpo = models.TextField(
        "Testo della mail",
        blank=True,
        help_text=(
            "Corpo precompilato nel client di posta dai filtri "
            "Non ritirate / Ritardo lavorazione. "
            "Segnaposto: {codice}, {cliente}, {nome}, {cognome}, {cellulare}, {telefono}."
        ),
    )

    class Meta:
        verbose_name = "Configurazione programma"
        verbose_name_plural = "Configurazioni programma"
        permissions = [
            ("access_parametri_programma", "Può gestire Parametri programma"),
        ]

    def __str__(self):
        return "Parametri programma"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "modalita_accettazione": cls.ModalitaAccettazione.STANDARD,
                "layout_stile": cls.LayoutStile.STANDARD,
                "barcode_iniziale": GS_BARCODE_DEFAULT,
            },
        )
        return obj

    @property
    def operatore_primo_nuova_riparazione(self):
        return self.modalita_accettazione == self.ModalitaAccettazione.OPERATORE_PRIMA

    @property
    def layout_compatto(self):
        return self.layout_stile == self.LayoutStile.COMPATTA
