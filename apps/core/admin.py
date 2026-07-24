from django.contrib import admin

from apps.core.models import Azienda, ConfigurazioneMssql, ConfigurazionePC, ConfigurazioneProgramma


@admin.register(Azienda)
class AziendaAdmin(admin.ModelAdmin):
    list_display = (
        "ragione_sociale",
        "partita_iva",
        "email",
        "comune",
        "is_active",
    )
    search_fields = (
        "ragione_sociale",
        "partita_iva",
        "codice_fiscale",
        "email",
        "pec",
        "comune",
    )
    list_filter = ("is_active", "provincia")


@admin.register(ConfigurazioneMssql)
class ConfigurazioneMssqlAdmin(admin.ModelAdmin):
    list_display = ("server", "nome_database", "utente", "attiva", "is_active")
    list_filter = ("attiva", "is_active")


@admin.register(ConfigurazionePC)
class ConfigurazionePCAdmin(admin.ModelAdmin):
    list_display = (
        "nome_pc",
        "descrizione",
        "negozio_default",
        "layout_stile",
        "is_active",
    )
    search_fields = ("nome_pc", "descrizione")
    list_filter = ("negozio_default", "layout_stile", "is_active")


@admin.register(ConfigurazioneProgramma)
class ConfigurazioneProgrammaAdmin(admin.ModelAdmin):
    list_display = (
        "modalita_accettazione",
        "layout_stile",
        "liste_righe_per_pagina",
        "comandi_voce_attivi",
        "barcode_iniziale",
        "webcam_tasto_scatto",
        "webcam_tasto_usa_foto",
        "webcam_tasto_nuovo_scatto",
        "is_active",
    )
    list_filter = ("modalita_accettazione", "layout_stile", "comandi_voce_attivi", "is_active")