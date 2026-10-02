"""Versione e pacchetto del client Windows LabRepair."""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings

from apps.core.version import get_version

_CLIENT_ZIP_RE = re.compile(
    r"^LabRepair_client_windows_(\d+(?:\.\d+)*)(?:[^/\\]*)?\.zip$",
    re.IGNORECASE,
)


def parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in re.split(r"[^\d]+", (value or "").strip()):
        if token.isdigit():
            parts.append(int(token))
    return tuple(parts) if parts else (0,)


def version_is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def get_client_package_dir() -> Path:
    configured = getattr(settings, "CLIENT_PACKAGE_DIR", None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / "installazione"


def find_client_package(preferred_version: str | None = None) -> tuple[Path | None, str]:
    """
    Trova lo zip client in installazione/.
    Preferisce il file con versione uguale a VERSION, altrimenti il più recente.
    Ritorna (path, versione_pacchetto).
    """
    folder = get_client_package_dir()
    preferred = (preferred_version or get_version()).strip()
    if not folder.is_dir():
        return None, preferred

    candidates: list[tuple[tuple[int, ...], str, Path]] = []
    for path in folder.glob("LabRepair_client_windows_*.zip"):
        match = _CLIENT_ZIP_RE.match(path.name)
        if not match:
            continue
        ver = match.group(1)
        candidates.append((parse_version(ver), ver, path))

    if not candidates:
        return None, preferred

    candidates.sort(key=lambda item: item[0], reverse=True)
    preferred_tuple = parse_version(preferred)
    for version_tuple, ver, path in candidates:
        if version_tuple == preferred_tuple:
            return path, ver
    _version_tuple, ver, path = candidates[0]
    return path, ver


def get_client_update_info() -> dict:
    package, package_version = find_client_package()
    info = {
        "version": package_version or get_version(),
        "available": bool(package and package.is_file()),
        "filename": package.name if package else "",
        "size": package.stat().st_size if package and package.is_file() else 0,
    }
    return info
