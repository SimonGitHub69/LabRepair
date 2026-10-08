from django.urls import path
from .views import (
    AziendaCreateView,
    AziendaDeleteView,
    AziendaListView,
    AziendaUpdateView,
    DashboardView,
    DocumentiView,
    NegozioCreateView,
    NegozioDeleteView,
    NegozioListView,
    NegozioUpdateView,
    NovitaView,
    ReportView,
    SistemaView,
    StatisticaExportView,
    StatisticaView,
    WebcamView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="index"),
    path("report/", ReportView.as_view(), name="report"),
    path("statistica/", StatisticaView.as_view(), name="statistica"),
    path("statistica/esporta/", StatisticaExportView.as_view(), name="statistica_export"),
    path("documenti/", DocumentiView.as_view(), name="documenti"),
    path("sistema/", SistemaView.as_view(), name="sistema"),
    path("sistema/novita/", NovitaView.as_view(), name="novita"),
    path("sistema/webcam/", WebcamView.as_view(), name="webcam"),
    path("parametri/negozi/", NegozioListView.as_view(), name="negozio_list"),
    path("parametri/negozi/nuovo/", NegozioCreateView.as_view(), name="negozio_create"),
    path("parametri/negozi/<int:pk>/modifica/", NegozioUpdateView.as_view(), name="negozio_update"),
    path("parametri/negozi/<int:pk>/elimina/", NegozioDeleteView.as_view(), name="negozio_delete"),
    path("sistema/aziende/", AziendaListView.as_view(), name="azienda_list"),
    path("sistema/aziende/nuova/", AziendaCreateView.as_view(), name="azienda_create"),
    path("sistema/aziende/<int:pk>/modifica/", AziendaUpdateView.as_view(), name="azienda_update"),
    path("sistema/aziende/<int:pk>/elimina/", AziendaDeleteView.as_view(), name="azienda_delete"),
]
