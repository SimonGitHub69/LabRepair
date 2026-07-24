from django.urls import path
from .views import (
    AziendaCreateView,
    AziendaDeleteView,
    AziendaListView,
    AziendaUpdateView,
    DashboardView,
    DocumentiView,
    SistemaView,
    WebcamView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="index"),
    path("documenti/", DocumentiView.as_view(), name="documenti"),
    path("sistema/", SistemaView.as_view(), name="sistema"),
    path("sistema/webcam/", WebcamView.as_view(), name="webcam"),
    path("sistema/aziende/", AziendaListView.as_view(), name="azienda_list"),
    path("sistema/aziende/nuova/", AziendaCreateView.as_view(), name="azienda_create"),
    path("sistema/aziende/<int:pk>/modifica/", AziendaUpdateView.as_view(), name="azienda_update"),
    path("sistema/aziende/<int:pk>/elimina/", AziendaDeleteView.as_view(), name="azienda_delete"),
]
