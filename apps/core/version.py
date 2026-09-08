"""Versione LabRepair e lettura del changelog."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = PROJECT_ROOT / "VERSION"
CHANGELOG_FILE = PROJECT_ROOT / "docs" / "CHANGELOG.md"

_HEADING_RE = re.compile(
    r"^#\s+\[([^\]]+)\]"
    r"(?:\s*[-–]\s*(\d{4}-\d{2}-\d{2}))?"
    r"(?:\s*\(([^)]+)\))?\s*$"
)


@lru_cache(maxsize=1)
def get_version() -> str:
    try:
        value = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        value = ""
    return value or "0.0.0"


def get_changelog_entries() -> list[dict]:
    try:
        text = CHANGELOG_FILE.read_text(encoding="utf-8")
    except OSError:
        return []

    entries: list[dict] = []
    current: dict | None = None
    section: dict | None = None
    in_fence = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            current = {
                "version": heading.group(1),
                "date": heading.group(2) or "",
                "status": heading.group(3) or "",
                "sections": [],
            }
            entries.append(current)
            section = None
            continue

        if current is None:
            continue

        if stripped.startswith("## "):
            section = {"title": stripped[3:].strip(), "items": []}
            current["sections"].append(section)
            continue

        if stripped.startswith("- ") and section is not None:
            section["items"].append(stripped[2:].strip())

    return entries


def get_latest_changelog() -> dict | None:
    entries = get_changelog_entries()
    return entries[0] if entries else None
