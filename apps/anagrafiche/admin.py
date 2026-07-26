from django.contrib import admin

from apps.anagrafiche.models import Anagrafica, Indirizzo


class IndirizzoInline(admin.TabularInline):
    model = Indirizzo
    extra = 0
    fields = (
        "tipo",
        "indirizzo",
        "civico",
        "cap",
        "comune",
        "provincia",
        "nazione",
        "principale",
        "is_active",
    )


@admin.register(Anagrafica)
class AnagraficaAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "tipo", "partita_iva", "email", "telefono", "is_active")
    search_fields = ("ragione_sociale", "cognome", "nome", "partita_iva", "codice_fiscale", "email", "telefono")
    list_filter = ("tipo", "is_active")
    inlines = (IndirizzoInline,)

    @admin.display(description="Denominazione", ordering="ragione_sociale")
    def denominazione(self, obj):
        return obj.display_name


# Indirizzo solo come inline (residenza cliente). Contatto SECURTEK non usato in LabRepair.
