"""Rilevamento stampanti Windows installate sul sistema (o su un PC remoto)."""

from __future__ import annotations

import json
import subprocess
import sys


def _run_printer_query(script: str) -> list[dict]:
    if sys.platform != "win32":
        return []

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=creationflags,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return []

    if result.returncode != 0:
        return []

    raw = (result.stdout or "").strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _merge_printer_rows(*sources: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for rows in sources:
        for row in rows or []:
            nome = str(row.get("Name") or row.get("nome") or "").strip()
            if not nome:
                continue
            key = nome.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    return merged


def _query_win32_printers(computer_name: str | None = None) -> list[dict]:
    computer = (computer_name or "").strip()
    if computer:
        safe = computer.replace("'", "''")
        script = (
            f"Get-CimInstance -ClassName Win32_Printer -ComputerName '{safe}' "
            "-ErrorAction SilentlyContinue | "
            "Select-Object Name, DriverName, PortName, "
            "@{N='Default';E={[bool]$_.Default}} | ConvertTo-Json -Compress"
        )
    else:
        script = (
            "Get-CimInstance -ClassName Win32_Printer -ErrorAction SilentlyContinue | "
            "Select-Object Name, DriverName, PortName, "
            "@{N='Default';E={[bool]$_.Default}} | ConvertTo-Json -Compress"
        )
    return _run_printer_query(script)


def _query_get_printer(computer_name: str | None = None) -> list[dict]:
    computer = (computer_name or "").strip()
    if computer:
        safe = computer.replace("'", "''")
        script = (
            f"Get-Printer -ComputerName '{safe}' -ErrorAction SilentlyContinue | "
            "Select-Object Name, DriverName, PortName, "
            "@{N='Default';E={[bool]$_.Default}} | ConvertTo-Json -Compress"
        )
    else:
        script = (
            "Get-Printer -ErrorAction SilentlyContinue | "
            "Select-Object Name, DriverName, PortName, "
            "@{N='Default';E={[bool]$_.Default}} | ConvertTo-Json -Compress"
        )
    return _run_printer_query(script)


def _normalize_rows(rows: list[dict]) -> list[dict]:
    printers = []
    seen = set()
    for row in rows:
        nome = str(row.get("Name") or "").strip()
        if not nome or nome.casefold() in seen:
            continue
        seen.add(nome.casefold())
        printers.append(
            {
                "nome": nome,
                "driver": str(row.get("DriverName") or "").strip(),
                "porta": str(row.get("PortName") or "").strip(),
                "predefinita": bool(row.get("Default")),
            }
        )
    printers.sort(key=lambda item: item["nome"].casefold())
    return printers


def list_installed_printers(computer_name: str | None = None) -> list[dict]:
    """
    Elenco stampanti installate sul PC dove gira questo processo.

    Ogni voce: {"nome": str, "driver": str, "porta": str, "predefinita": bool}.

    Non esegue query WMI/WinRM remote (bloccano Waitress sui client).
    Per le stampanti dei PC client usare l'agent locale (127.0.0.1:17346).
    """
    del computer_name  # mantenuto per compatibilita' chiamate esistenti
    # Get-Printer e' piu' veloce; Win32 solo se non restituisce nulla.
    rows = _query_get_printer(None)
    if not rows:
        rows = _query_win32_printers(None)
    return _normalize_rows(rows)


def list_installed_printer_names(computer_name: str | None = None) -> list[str]:
    return [item["nome"] for item in list_installed_printers(computer_name)]


def normalize_stampanti(value) -> list[str]:
    """Normalizza elenco stampanti salvato (JSON / form) a lista di nomi unici."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = [part.strip() for part in text.splitlines() if part.strip()]

    names = []
    seen = set()
    if isinstance(value, dict):
        value = value.get("stampanti") or value.get("names") or list(value.values())
    if not isinstance(value, (list, tuple)):
        return []

    for item in value:
        if isinstance(item, dict):
            nome = str(item.get("nome") or item.get("name") or "").strip()
        else:
            nome = str(item or "").strip()
        if not nome:
            continue
        key = nome.casefold()
        if key in seen:
            continue
        seen.add(key)
        names.append(nome)
    return names


def sync_stampanti_payload(printers, user=None, configurazione_pc=None) -> dict:
    """Allinea la tabella Stampante a un elenco gia' rilevato (es. agent locale PC client)."""
    detected = []
    if isinstance(printers, list):
        for item in printers:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("nome") or item.get("name") or item.get("Name") or "").strip()
            if not nome:
                continue
            detected.append(
                {
                    "nome": nome,
                    "driver": str(item.get("driver") or item.get("DriverName") or "").strip(),
                    "porta": str(item.get("porta") or item.get("PortName") or "").strip(),
                    "predefinita": bool(item.get("predefinita") or item.get("Default")),
                }
            )
    return _sync_stampanti_rows(detected, user=user, configurazione_pc=configurazione_pc)


def _sync_stampanti_rows(detected: list[dict], user=None, configurazione_pc=None) -> dict:
    from apps.core.models.stampante import Stampante

    created = 0
    updated = 0
    names = []

    for item in detected:
        nome = item["nome"]
        names.append(nome)
        existing_qs = Stampante.objects.filter(nome__iexact=nome)
        if configurazione_pc is not None:
            existing = (
                existing_qs.filter(configurazione_pc=configurazione_pc)
                .order_by("-is_active", "id")
                .first()
            )
            if existing is None:
                # Riaggancia eventuale record orfano (pre-migrazione).
                existing = (
                    existing_qs.filter(configurazione_pc__isnull=True)
                    .order_by("-is_active", "id")
                    .first()
                )
        else:
            existing = (
                existing_qs.filter(configurazione_pc__isnull=True)
                .order_by("-is_active", "id")
                .first()
            )
        if existing:
            changed = False
            if configurazione_pc is not None and existing.configurazione_pc_id != configurazione_pc.pk:
                existing.configurazione_pc = configurazione_pc
                changed = True
            if not existing.is_active:
                existing.is_active = True
                existing.deleted_at = None
                existing.deleted_by = None
                changed = True
            if (existing.porta or "") != (item.get("porta") or ""):
                existing.porta = item.get("porta") or ""
                changed = True
            if (existing.driver or "") != (item.get("driver") or ""):
                existing.driver = item.get("driver") or ""
                changed = True
            if bool(existing.predefinita) != bool(item.get("predefinita")):
                existing.predefinita = bool(item.get("predefinita"))
                changed = True
            # Allinea il casing del nome Windows se cambia.
            if existing.nome != nome:
                existing.nome = nome
                changed = True
            if changed:
                if user is not None:
                    existing.updated_by = user
                existing.save()
                updated += 1
        else:
            Stampante.objects.create(
                configurazione_pc=configurazione_pc,
                nome=nome,
                porta=item.get("porta") or "",
                driver=item.get("driver") or "",
                predefinita=bool(item.get("predefinita")),
                created_by=user,
                updated_by=user,
            )
            created += 1

    return {
        "created": created,
        "updated": updated,
        "total": len(names),
        "names": names,
    }


def sync_stampanti_rilevate(
    computer_name: str | None = None,
    user=None,
    configurazione_pc=None,
) -> dict:
    """
    Allinea la tabella Stampante alle stampanti installate sul sistema.

    Crea le mancanti, aggiorna porta/driver/predefinita, non tocca
    descrizione e gap gia' impostati dall'utente.
    """
    detected = list_installed_printers(computer_name)
    return _sync_stampanti_rows(detected, user=user, configurazione_pc=configurazione_pc)


def sync_stampanti_for_postazione(postazione, user=None) -> dict:
    """Allinea i record Stampante alla selezione salvata su ConfigurazionePC."""
    from apps.core.models.stampante import Stampante

    nomi = postazione.stampanti_elenco if postazione is not None else []
    selected = {nome.casefold() for nome in nomi}
    detected_by_name = {
        str(item.get("nome") or "").casefold(): item
        for item in list_installed_printers(None)
        if str(item.get("nome") or "").strip()
    }
    rows = []
    for nome in nomi:
        item = detected_by_name.get(nome.casefold())
        if item:
            rows.append(item)
        else:
            rows.append(
                {
                    "nome": nome,
                    "driver": "",
                    "porta": "",
                    "predefinita": False,
                }
            )
    result = _sync_stampanti_rows(rows, user=user, configurazione_pc=postazione)

    if postazione is not None and nomi:
        for stampante in Stampante.objects.filter(configurazione_pc=postazione, is_active=True):
            if stampante.nome.casefold() not in selected:
                stampante.soft_delete(user=user)
    elif postazione is not None and not nomi:
        for stampante in Stampante.objects.filter(configurazione_pc=postazione, is_active=True):
            stampante.soft_delete(user=user)

    return result


def get_stampante_busta_for_request(request):
    """
    Stampante da usare per i gap busta: preferisce quelle collegate al PC
    corrente (predefinita se presente), altrimenti la predefinita di sistema.
    """
    from django.db.models import Q

    from apps.core.models.stampante import Stampante
    from apps.core.pc import get_configurazione_pc_for_request

    base = Stampante.objects.filter(is_active=True)
    cfg = get_configurazione_pc_for_request(request) if request is not None else None

    if cfg:
        linked = list(base.filter(configurazione_pc=cfg).order_by("nome"))
        if linked:
            for stampante in linked:
                if stampante.predefinita:
                    return stampante
            return linked[0]

        names = cfg.stampanti_elenco
        if names:
            name_filter = Q()
            for nome in names:
                name_filter |= Q(nome__iexact=nome)
            linked = list(base.filter(name_filter).order_by("nome"))
            if linked:
                for stampante in linked:
                    if stampante.predefinita:
                        return stampante
                return linked[0]

    preferred = base.filter(predefinita=True).order_by("nome").first()
    if preferred:
        return preferred
    return base.order_by("nome").first()


def busta_gap_css_vars(stampante) -> dict:
    """Valori CSS per gap parte A / parte B (mm)."""
    from decimal import Decimal

    def _mm(value) -> str:
        try:
            amount = Decimal(value if value is not None else "0")
        except Exception:
            amount = Decimal("0")
        return f"{amount.quantize(Decimal('0.01'))}mm"

    if stampante is None:
        return {
            "gap_busta_superiore_css": "0.00mm",
            "gap_busta_inferiore_css": "0.00mm",
        }
    return {
        "gap_busta_superiore_css": _mm(stampante.gap_busta_superiore),
        "gap_busta_inferiore_css": _mm(stampante.gap_busta_inferiore),
    }
