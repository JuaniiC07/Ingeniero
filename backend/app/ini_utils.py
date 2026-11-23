from __future__ import annotations

import re
from dataclasses import dataclass

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]")
KV_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$")


def strip_comment(value: str) -> str:
    for marker in (";", "//"):
        index = value.find(marker)
        if index >= 0:
            value = value[:index]
    return value.strip()


def parse_sections(text: str) -> dict[str, dict[str, str]]:
    """Parse a generic AC .ini (setup.ini, ui_track.json is separate)."""
    data: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "//", "#")):
            continue
        header = SECTION_RE.match(line)
        if header:
            current = header.group(1).strip().upper()
            data.setdefault(current, {})
            continue
        if current is None:
            continue
        kv = KV_RE.match(line)
        if not kv:
            continue
        key = kv.group(1).strip().upper()
        value = strip_comment(kv.group(2))
        data[current][key] = value
    return data


def as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


@dataclass
class SpecParam:
    section: str
    name: str
    tab: str
    minimum: float | None
    maximum: float | None
    step: float | None
    show_clicks: int
    help: str
    lut: str | None
    raw: dict[str, str]
