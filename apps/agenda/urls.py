from django.urls import path

from apps.agenda.views import (
    AgendaCalendarView,
    AgendaDayView,
    ConfigurazionePCCreateView,
    ConfigurazionePCDeleteView,
    ConfigurazionePCListView,
    ConfigurazionePCUpdateView,
    ParametriComandiVoceView,
    ParametriProgrammaView,
    ParametriSistemaView,
    EventoAgendaCreateView,
    EventoAgendaDeleteView,
    EventoAgendaUpdateView,
)

app_name = "agenda"

urlpatterns = [
    path("", AgendaCalendarView.as_view(), name="calendar"),
    path("giorno/", AgendaDayView.as_view(), name="day"),
    path("parametri-mail/", ParametriSistemaView.as_view(), name="configurazione_email"),
    path("parametri-programma/", ParametriProgrammaView.as_view(), name="configurazione_programma"),
    path("comandi-vocali/", ParametriComandiVoceView.as_view(), name="comandi_voce"),
    path("parametri-pc/", ConfigurazionePCListView.as_view(), name="configurazione_pc_list"),
    path("parametri-pc/nuovo/", ConfigurazionePCCreateView.as_view(), name="configurazione_pc_create"),
    path("parametri-pc/<int:pk>/modifica/", ConfigurazionePCUpdateView.as_view(), name="configurazione_pc_update"),
    path("parametri-pc/<int:pk>/elimina/", ConfigurazionePCDeleteView.as_view(), name="configurazione_pc_delete"),
    path("nuovo/", EventoAgendaCreateView.as_view(), name="evento_create"),
    path("<int:pk>/modifica/", EventoAgendaUpdateView.as_view(), name="evento_update"),
    path("<int:pk>/elimina/", EventoAgendaDeleteView.as_view(), name="evento_delete"),
]
