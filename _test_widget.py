import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from apps.core.widgets import NoAutofillTextInput
html = NoAutofillTextInput().render("cognome", "x", {"id": "id_cognome"})
has_ta = "textarea" in html.lower()
has_h = "hidden" in html.lower()
print("OK" if has_ta and has_h else "FAIL")
print("textarea:", has_ta, "hidden:", has_h)
print(html)
