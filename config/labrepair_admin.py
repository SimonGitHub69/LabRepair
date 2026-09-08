"""
Admin Django riorganizzato come il menu LabRepair.

Come aggiornare il menu
-----------------------
Modifica solo la tupla ADMIN_MENU_SECTIONS qui sotto, poi riavvia Waitress.

Formati voce:
  ("app.modello", "Etichetta opzionale")
      -> apre la pagina Django Admin del modello registrato
  ("__link__", "Etichetta", "namespace:url_name")
      -> apre una pagina LabRepair (stesse maschere del sidebar)
  ("__link__", "Etichetta", "namespace:url_name", "app.permesso")
      -> come sopra, ma solo se l'utente ha il permesso
  ("__link__", "Etichetta", "#")
      -> voce disabilitata / placeholder
"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import reverse


# Sezioni allineate a templates/base/sidebar.html
ADMIN_MENU_SECTIONS = (
    {
        "name": "Dashboard",
        "app_label": "labrepair_dashboard",
        "models": (
            ("__link__", "Dashboard", "dashboard:index"),
        ),
    },
    {
        "name": "Gestione",
        "app_label": "labrepair_gestione",
        "models": (
            ("__link__", "Riparazioni", "pratiche:pratica_list"),
            ("__link__", "Anagrafiche", "anagrafiche:anagrafica_list"),
            ("__link__", "Riparatori", "pratiche:studio_tecnico_list"),
            ("__link__", "Agenda", "agenda:calendar"),
            (
                "__link__",
                "Documenti",
                "dashboard:documenti",
                "dashboard.access_documenti",
            ),
        ),
    },
    {
        "name": "Analisi",
        "app_label": "labrepair_analisi",
        "models": (
            ("__link__", "Report", "dashboard:report", "dashboard.access_report"),
        ),
    },
    {
        "name": "Strumenti",
        "app_label": "labrepair_strumenti",
        "models": (
            (
                "__link__",
                "Importa clienti CSV",
                "anagrafiche:import_clienti_csv",
                "anagrafiche.import_clienti_csv",
            ),
        ),
    },
    {
        "name": "Parametri",
        "app_label": "labrepair_parametri",
        "models": (
            ("__link__", "Operatori", "pratiche:operatore_list"),
            ("__link__", "Tipi di oggetto", "pratiche:tipo_oggetto_list"),
            (
                "__link__",
                "Parametri PC",
                "agenda:configurazione_pc_list",
                "dashboard.access_parametri_pc",
            ),
            (
                "__link__",
                "Parametri mail e SQL",
                "agenda:configurazione_email",
                "agenda.access_parametri_mail_sql",
            ),
            (
                "__link__",
                "Parametri programma",
                "agenda:configurazione_programma",
                "core.access_parametri_programma",
            ),
            (
                "__link__",
                "Comandi vocali",
                "agenda:comandi_voce",
                "dashboard.access_comandi_vocali",
            ),
        ),
    },
    {
        "name": "Sistema",
        "app_label": "labrepair_sistema",
        "models": (
            ("__link__", "Aziende", "dashboard:azienda_list"),
            ("__link__", "Sistema", "dashboard:sistema", "dashboard.access_sistema"),
            ("__link__", "Novità", "dashboard:novita", "dashboard.access_sistema"),
        ),
    },
    {
        "name": "Autenticazione",
        "app_label": "labrepair_auth",
        "models": (
            # Restano in Django Admin (utenti/gruppi)
            ("auth.user", "Utenti"),
            ("accounts.user", "Utenti"),
            ("auth.group", "Gruppi"),
        ),
    },
)


def _custom_link_entry(name, url):
    # Stesso formato delle voci modello, cosi' compare nome + "Modifica" in Admin.
    return {
        "name": name,
        "object_name": name,
        "admin_url": url,
        "add_url": None,
        "view_only": False,
        "perms": {"add": False, "change": True, "delete": False, "view": True},
    }


class LabRepairAdminSite(AdminSite):
    site_header = "Amministrazione LabRepair"
    site_title = "LabRepair"
    index_title = "Amministrazione LabRepair"

    def get_app_list(self, request, app_label=None):
        """Ricostruisce l'indice Admin per sezioni del menu LabRepair."""
        original = super().get_app_list(request, app_label=None)
        by_label = {}
        for app in original:
            for model in app.get("models", []):
                key = f"{app['app_label']}.{model['object_name'].lower()}"
                by_label[key] = model

        app_list = []
        used = set()
        for section in ADMIN_MENU_SECTIONS:
            models_out = []
            for item in section["models"]:
                model_key = item[0]
                if model_key == "__link__":
                    _, display_name, url_ref, *rest = item
                    required_perm = rest[0] if rest else None
                    if required_perm and not request.user.has_perm(required_perm):
                        continue
                    try:
                        url = reverse(url_ref) if ":" in url_ref else url_ref
                    except Exception:
                        url = url_ref
                    models_out.append(_custom_link_entry(display_name, url))
                    continue

                display_name = item[1] if len(item) > 1 else None
                model_dict = by_label.get(model_key)
                if not model_dict:
                    continue
                if model_key in used:
                    continue
                entry = dict(model_dict)
                if display_name:
                    entry["name"] = display_name
                models_out.append(entry)
                used.add(model_key)

            if not models_out:
                continue

            if app_label and section["app_label"] != app_label:
                continue

            app_list.append(
                {
                    "name": section["name"],
                    "app_label": section["app_label"],
                    "app_url": "/admin/",
                    "has_module_perms": True,
                    "models": models_out,
                }
            )

        if app_label:
            app_list = [app for app in app_list if app["app_label"] == app_label]

        return app_list


def apply_labrepair_admin():
    """Sostituisce admin.site con LabRepairAdminSite preservando le registrazioni."""
    from django.contrib.admin import sites as admin_sites

    current = admin_sites.site
    if isinstance(current, LabRepairAdminSite):
        return current

    custom = LabRepairAdminSite(name="admin")
    custom._registry = current._registry.copy()
    for model, model_admin in custom._registry.items():
        model_admin.admin_site = custom

    admin_sites.site = custom
    admin.site = custom
    return custom
