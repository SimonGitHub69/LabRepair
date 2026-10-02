from django.core.management.base import BaseCommand

from apps.pratiche.gs_vendite import STATI_PENDING_DEFAULT, sync_pagamenti_cassa_pending
from apps.pratiche.models import Pratica


class Command(BaseCommand):
    help = (
        "Legge GS_VENDITE_DETTAGLIO dal Database Cassa e aggiorna "
        "Prezzo pagato / stato Evasa sulle riparazioni."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--negozio",
            default="",
            help="Filtra per codice negozio (es. PT). Vuoto = tutti.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Massimo riparazioni da controllare (default 500).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo lettura: non scrive su LabRepair.",
        )
        parser.add_argument(
            "--tutti-stati",
            action="store_true",
            help="Controlla tutti gli stati tranne Annullata/Archiviata (non solo In consegna).",
        )

    def handle(self, *args, **options):
        negozio = (options.get("negozio") or "").strip().upper() or None
        dry_run = bool(options.get("dry_run"))
        limit = options.get("limit") or 500

        stati = None
        if options.get("tutti_stati"):
            stati = {
                value
                for value, _label in Pratica.Stato.choices
                if value
                not in {Pratica.Stato.ANNULLATA, Pratica.Stato.ARCHIVIATA}
            }
        else:
            stati = set(STATI_PENDING_DEFAULT)

        self.stdout.write(
            f"Sync pagamenti cassa"
            f"{' (dry-run)' if dry_run else ''}"
            f" · negozio={negozio or 'tutti'}"
            f" · stati={', '.join(sorted(stati))}"
            f" · limit={limit}"
        )

        stats = sync_pagamenti_cassa_pending(
            negozio=negozio,
            stati=stati,
            limit=limit,
            dry_run=dry_run,
        )

        if stats.get("skipped"):
            self.stdout.write(
                self.style.WARNING(
                    "Collegamento MS-SQL / Database Cassa non attivo o incompleto."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Controllate={stats['checked']} "
                f"trovate={stats['found']} "
                f"aggiornate={stats['updated']} "
                f"errori={stats['errors']}"
            )
        )
