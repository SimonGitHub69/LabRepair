import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.core.models import ConfigurazioneProgramma

cfg = ConfigurazioneProgramma.get_solo()
cfg.comandi_voce_attivi = True
cfg.liste_righe_per_pagina = 10
cfg.save(update_fields=["comandi_voce_attivi", "liste_righe_per_pagina", "updated_at"])

admin = get_user_model().objects.filter(is_superuser=True).first()
client = Client(HTTP_HOST="127.0.0.1")
client.force_login(admin)
session = client.session
session["labrepair_app"] = True
session["negozio"] = "PT"
session.save()

r = client.get(reverse("pratiche:pratica_list"))
html = r.content.decode("utf-8", "replace")
print("list", r.status_code)
print("has_page_size", 'data-page-size-select' in html)
print("has_jump", "data-page-jump" in html)
print("has_first", "ti-chevrons-left" in html)
print("page_size_10_selected", 'value="10" selected' in html or "value=\"10\" selected" in html)
print("voice_btn", "stVoiceCommandBtn" in html)
print("voice_js", "voice_commands.js" in html)

r2 = client.get(reverse("agenda:configurazione_programma"))
h2 = r2.content.decode("utf-8", "replace")
print("parametri", r2.status_code)
print("has_voce_card", "Comandi vocali" in h2)
print("has_righe", "Righe per pagina" in h2)
