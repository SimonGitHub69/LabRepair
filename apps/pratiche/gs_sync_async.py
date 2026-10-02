"""Sync MS-SQL in background: non blocca Salva / elenco riparazioni."""

from __future__ import annotations

import logging
import threading

from django.db import close_old_connections

logger = logging.getLogger(__name__)


def run_in_background(target, *args, **kwargs):
    def runner():
        close_old_connections()
        try:
            target(*args, **kwargs)
        except Exception:
            logger.exception("Task background LabRepair fallito: %s", getattr(target, "__name__", target))
        finally:
            close_old_connections()

    thread = threading.Thread(target=runner, name="labrepair-bg-sync", daemon=True)
    thread.start()
    return thread


def schedule_gs_articolo_sync(pratica_id, user_id):
    if not pratica_id:
        return

    def job():
        from django.contrib.auth import get_user_model

        from apps.pratiche.gs_articoli import sync_pratica_to_gs_articoli
        from apps.pratiche.models import Pratica

        pratica = (
            Pratica.objects.filter(pk=pratica_id, is_active=True)
            .select_related("tipo_oggetto")
            .first()
        )
        if not pratica:
            return
        user = get_user_model().objects.filter(pk=user_id).first()
        result = sync_pratica_to_gs_articoli(pratica, user)
        if result and not result.ok:
            logger.warning("Sync TB_PREZZICASSE (bg): %s", result.message)

    run_in_background(job)


def schedule_pagamento_da_cassa(pratica_id):
    if not pratica_id:
        return

    def job():
        from apps.pratiche.gs_vendite import sync_pagamento_da_cassa
        from apps.pratiche.models import Pratica

        pratica = Pratica.objects.filter(pk=pratica_id, is_active=True).first()
        if not pratica:
            return
        result = sync_pagamento_da_cassa(pratica)
        if result and not result.ok:
            logger.warning("Sync pagamento cassa (bg): %s", result.message)
        elif result and result.updated:
            logger.info("Sync pagamento cassa (bg): %s", result.message)

    run_in_background(job)


def schedule_pagamenti_cassa_pending(*, negozio=None, limit=200):
    def job():
        from apps.pratiche.gs_vendite import sync_pagamenti_cassa_pending

        stats = sync_pagamenti_cassa_pending(negozio=negozio, limit=limit)
        if stats.get("skipped"):
            logger.info(
                "Sync pagamenti cassa (bg): saltata (MS-SQL/cassa non attivo o incompleto)."
            )
        elif stats.get("checked") == 0:
            logger.info(
                "Sync pagamenti cassa (bg): nessuna riparazione candidata (stati aperti)."
            )
        elif stats.get("updated"):
            logger.info(
                "Sync pagamenti cassa (bg): aggiornate=%s trovate=%s controllate=%s",
                stats.get("updated"),
                stats.get("found"),
                stats.get("checked"),
            )
        else:
            logger.info(
                "Sync pagamenti cassa (bg): controllate=%s trovate=%s aggiornate=0",
                stats.get("checked"),
                stats.get("found"),
            )
        if stats.get("errors"):
            logger.warning("Sync pagamenti cassa (bg): errori=%s", stats.get("errors"))

    run_in_background(job)
