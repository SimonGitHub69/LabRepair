from django.contrib import admin, messages

from apps.pratiche.gs_articoli import sync_pratica_to_gs_articoli
from apps.pratiche.models import (
    Operatore,
    Pratica,
    StudioTecnico,
    TipoOggetto,
)

# Solo le voci allineate al menu LabRepair:
# Riparazioni, Riparatori, Operatori, Tipi di oggetto


@admin.register(Pratica)
class PraticaAdmin(admin.ModelAdmin):
    list_display = (
        "codice",
        "cliente",
        "tipo_oggetto",
        "tipo_metallo",
        "tipologia",
        "stato",
        "operatore",
        "riparatore",
        "data_scadenza",
        "prezzo_al",
        "is_active",
    )
    search_fields = (
        "codice",
        "titolo",
        "tipo_oggetto__denominazione",
        "riparatore__denominazione",
        "operatore__nominativo",
        "cliente__ragione_sociale",
    )
    list_filter = ("stato", "tipologia", "tipo_metallo", "priorita", "operatore", "is_active")
    autocomplete_fields = (
        "cliente",
        "responsabile",
        "operatore",
        "tipo_oggetto",
        "riparatore",
        "centro_assistenza",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        result = sync_pratica_to_gs_articoli(obj, request.user)
        if not result.ok:
            self.message_user(request, result.message, level=messages.WARNING)


@admin.register(StudioTecnico)
class StudioTecnicoAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "email", "telefono", "is_active")
    search_fields = ("denominazione", "email", "telefono")
    list_filter = ("is_active",)


@admin.register(Operatore)
class OperatoreAdmin(admin.ModelAdmin):
    list_display = ("nominativo", "is_active")
    search_fields = ("nominativo",)
    list_filter = ("is_active",)


@admin.register(TipoOggetto)
class TipoOggettoAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "um", "is_active")
    search_fields = ("denominazione", "descrizione")
    list_filter = ("um", "is_active")
