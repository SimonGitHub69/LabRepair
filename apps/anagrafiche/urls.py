from django.urls import path

from .views import (
    AnagraficaListView,
    AnagraficaCreateView,
    AnagraficaUpdateView,
    AnagraficaDetailView,
    AnagraficaDeleteView,
    AnagraficaDocumentoUpdateJsonView,
    ContattoCreateView,
    ContattoUpdateView,
    ContattoDeleteView,
    IndirizzoCreateView,
    IndirizzoUpdateView,
    IndirizzoDeleteView,
    ImportClientiCsvView,
    AnagraficaCieReadView,
)

app_name = "anagrafiche"

urlpatterns = [
    path("", AnagraficaListView.as_view(), name="anagrafica_list"),
    path("nuova/", AnagraficaCreateView.as_view(), name="anagrafica_create"),
    path("importa-csv/", ImportClientiCsvView.as_view(), name="import_clienti_csv"),
    path("cie/leggi/", AnagraficaCieReadView.as_view(), name="cie_leggi"),
    path("<int:pk>/modifica/", AnagraficaUpdateView.as_view(), name="anagrafica_update"),
    path("<int:pk>/documento/", AnagraficaDocumentoUpdateJsonView.as_view(), name="documento_update"),
    path("<int:pk>/elimina/", AnagraficaDeleteView.as_view(), name="anagrafica_delete"),
    path("<int:anagrafica_pk>/contatti/nuovo/", ContattoCreateView.as_view(), name="contatto_create"),
    path("<int:anagrafica_pk>/contatti/<int:pk>/modifica/", ContattoUpdateView.as_view(), name="contatto_update"),
    path("<int:anagrafica_pk>/contatti/<int:pk>/elimina/", ContattoDeleteView.as_view(), name="contatto_delete"),
    path("<int:anagrafica_pk>/indirizzi/nuovo/", IndirizzoCreateView.as_view(), name="indirizzo_create"),
    path("<int:anagrafica_pk>/indirizzi/<int:pk>/modifica/", IndirizzoUpdateView.as_view(), name="indirizzo_update"),
    path("<int:anagrafica_pk>/indirizzi/<int:pk>/elimina/", IndirizzoDeleteView.as_view(), name="indirizzo_delete"),
    path("<int:pk>/", AnagraficaDetailView.as_view(), name="anagrafica_detail"),
]
