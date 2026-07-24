from django.core.management.base import BaseCommand
from django.db import transaction

from apps.anagrafiche.models import Anagrafica
from apps.anagrafiche.name_case import format_cognome, format_nome


class Command(BaseCommand):
    help = (
        "Normalizza l'archivio anagrafiche: cognomi in MAIUSCOLO, "
        "nomi con Prima lettera maiuscola."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quante anagrafiche verrebbero aggiornate senza salvare.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = Anagrafica.objects.filter(is_active=True).order_by("id")
        total = qs.count()
        updated = 0

        self.stdout.write(f"Anagrafiche attive da verificare: {total}")

        with transaction.atomic():
            for anagrafica in qs.iterator(chunk_size=500):
                if anagrafica.tipo != Anagrafica.Tipo.CLIENTE:
                    continue

                new_cognome = format_cognome(anagrafica.cognome)
                new_nome = format_nome(anagrafica.nome)
                new_ragione = f"{new_cognome} {new_nome}".strip() or anagrafica.ragione_sociale

                if (
                    anagrafica.cognome == new_cognome
                    and anagrafica.nome == new_nome
                    and anagrafica.ragione_sociale == new_ragione
                ):
                    continue

                updated += 1
                if dry_run:
                    continue

                anagrafica.cognome = new_cognome
                anagrafica.nome = new_nome
                anagrafica.ragione_sociale = new_ragione
                anagrafica.save(
                    update_fields=["cognome", "nome", "ragione_sociale", "updated_at"]
                )

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"Dry-run: {updated} anagrafiche da aggiornare.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Aggiornate {updated} anagrafiche.")
            )
