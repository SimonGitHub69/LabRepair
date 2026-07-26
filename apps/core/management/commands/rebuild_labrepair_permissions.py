from django.core.management.base import BaseCommand
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


# Catalogo privilegi operativi LabRepair (niente sessions/contenttypes/admin log).
BASE_PERMISSIONS = (
    "anagrafiche.add_anagrafica",
    "anagrafiche.change_anagrafica",
    "anagrafiche.delete_anagrafica",
    "anagrafiche.view_anagrafica",
    "pratiche.add_pratica",
    "pratiche.change_pratica",
    "pratiche.delete_pratica",
    "pratiche.view_pratica",
    "pratiche.add_comunicazionepratica",
    "pratiche.change_comunicazionepratica",
    "pratiche.delete_comunicazionepratica",
    "pratiche.view_comunicazionepratica",
    "pratiche.add_praticafoto",
    "pratiche.change_praticafoto",
    "pratiche.delete_praticafoto",
    "pratiche.view_praticafoto",
    "pratiche.add_operatore",
    "pratiche.change_operatore",
    "pratiche.delete_operatore",
    "pratiche.view_operatore",
    "pratiche.add_studiotecnico",
    "pratiche.change_studiotecnico",
    "pratiche.delete_studiotecnico",
    "pratiche.view_studiotecnico",
    "pratiche.add_tipooggetto",
    "pratiche.change_tipooggetto",
    "pratiche.delete_tipooggetto",
    "pratiche.view_tipooggetto",
    "agenda.add_eventoagenda",
    "agenda.change_eventoagenda",
    "agenda.delete_eventoagenda",
    "agenda.view_eventoagenda",
    "core.view_azienda",
    "core.add_configurazionepc",
    "core.change_configurazionepc",
    "core.delete_configurazionepc",
    "core.view_configurazionepc",
    "dashboard.access_documenti",
    "dashboard.access_report",
    "dashboard.access_comandi_vocali",
    "dashboard.access_parametri_pc",
    "dashboard.access_sistema",
    "auth.view_user",
    "auth.view_group",
)

FULL_NEGOZIO_EXTRA = (
    "anagrafiche.import_clienti_csv",
    "agenda.access_parametri_mail_sql",
    "agenda.add_configurazionenotificaemail",
    "agenda.change_configurazionenotificaemail",
    "agenda.delete_configurazionenotificaemail",
    "agenda.view_configurazionenotificaemail",
    "core.access_parametri_programma",
    "core.add_azienda",
    "core.change_azienda",
    "core.delete_azienda",
    "core.add_configurazionemssql",
    "core.change_configurazionemssql",
    "core.delete_configurazionemssql",
    "core.view_configurazionemssql",
    "core.add_configurazioneprogramma",
    "core.change_configurazioneprogramma",
    "core.delete_configurazioneprogramma",
    "core.view_configurazioneprogramma",
    "auth.add_user",
    "auth.change_user",
    "auth.delete_user",
    "auth.add_group",
    "auth.change_group",
    "auth.delete_group",
)

GROUP_MATRIX = {
    "Montale": BASE_PERMISSIONS + FULL_NEGOZIO_EXTRA,
    "Quarrata": BASE_PERMISSIONS + FULL_NEGOZIO_EXTRA,
    "Pistoia": BASE_PERMISSIONS,
}


def _perm_key(permission):
    return f"{permission.content_type.app_label}.{permission.codename}"


class Command(BaseCommand):
    help = (
        "Sincronizza i privilegi Django dai modelli e, con --reset-groups, "
        "azzera e ricostruisce i privilegi dei gruppi negozio LabRepair."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-groups",
            action="store_true",
            help="Azzera e riassegna i privilegi dei gruppi Montale/Quarrata/Pistoia.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra solo cosa verrebbe fatto.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reset_groups = options["reset_groups"]

        self.stdout.write("1) Creazione/aggiornamento privilegi dai modelli…")
        if not dry_run:
            for app_config in apps.get_app_configs():
                create_permissions(app_config, verbosity=0)

        # Rimuove ContentType orfani (modelli non più esistenti).
        stale_cts = []
        for ct in ContentType.objects.all():
            try:
                apps.get_model(ct.app_label, ct.model)
            except LookupError:
                stale_cts.append(ct)
        if stale_cts:
            self.stdout.write(f"   ContentType orfani: {len(stale_cts)}")
            for ct in stale_cts:
                self.stdout.write(f"   - {ct.app_label}.{ct.model}")
                if not dry_run:
                    Permission.objects.filter(content_type=ct).delete()
                    ct.delete()
        else:
            self.stdout.write("   Nessun ContentType orfano.")

        total = Permission.objects.count()
        self.stdout.write(self.style.SUCCESS(f"   Privilegi in catalogo: {total}"))

        if not reset_groups:
            self.stdout.write(
                "Catalogo sincronizzato. Per azzerare i gruppi negozio riesegui con --reset-groups."
            )
            return

        self.stdout.write("2) Azzeramento e ricostruzione gruppi negozio…")
        all_perms = {_perm_key(p): p for p in Permission.objects.select_related("content_type")}
        for group_name, wanted_keys in GROUP_MATRIX.items():
            group, created = Group.objects.get_or_create(name=group_name)
            missing = [key for key in wanted_keys if key not in all_perms]
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"   {group_name}: privilegi non trovati nel catalogo: {', '.join(missing)}"
                    )
                )
            selected = [all_perms[key] for key in wanted_keys if key in all_perms]
            self.stdout.write(
                f"   {group_name}: {'creato, ' if created else ''}"
                f"{group.permissions.count()} -> {len(selected)} privilegi"
            )
            if not dry_run:
                group.permissions.set(selected)

        self.stdout.write(self.style.SUCCESS("Ricostruzione completata."))
