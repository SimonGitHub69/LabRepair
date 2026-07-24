from django.core.management.base import BaseCommand, CommandError

from apps.anagrafiche.import_clienti import format_import_stats, import_clienti_csv


class Command(BaseCommand):
    help = "Importa clienti da CSV (formato tracciato Pistoia, separatore ;)."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            help="Percorso del file CSV da importare.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula l'import senza scrivere sul database.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Aggiorna i clienti gia' presenti (match su codice fiscale).",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        try:
            stats = import_clienti_csv(
                csv_file,
                dry_run=dry_run,
                update_existing=update_existing,
            )
        except OSError as exc:
            raise CommandError(f"Impossibile leggere il file CSV: {exc}") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(format_import_stats(stats, dry_run=dry_run)))
