from __future__ import annotations

from pathlib import Path

from app.ini_utils import parse_sections
from app.setup_io import SetupFile, format_number


def read_preset(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        sections = parse_sections(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}
    preset = sections.get("PRESET_0") or next(iter(sections.values()), {})
    out: dict[str, float] = {}
    for key, value in preset.items():
        try:
            out[key] = float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            continue
    return out


def check(setup_path: str | None) -> list[str]:
    if not setup_path:
        return []
    ini_path = Path(setup_path)
    sp_path = ini_path.with_suffix(".sp")
    if not sp_path.exists():
        return []
    setup = SetupFile.from_path(ini_path)
    preset = read_preset(sp_path)
    if not preset:
        return [f"Se encontró {sp_path.name}, pero no se pudo leer como preset de boxes."]
    warnings: list[str] = []
    for key in ("PRESSURE_LF", "PRESSURE_RF", "PRESSURE_LR", "PRESSURE_RR"):
        if key not in preset:
            continue
        ini_value = setup.get_float(key)
        sp_value = preset.get(key)
        if ini_value is None or sp_value is None:
            continue
        if abs(ini_value - sp_value) > 0.5:
            warnings.append(
                f"El preset de boxes ({sp_path.name}) tiene {key}={format_number(sp_value, 2)}, "
                f"pero el setup tiene {format_number(ini_value, 2)}. "
                "Content Manager no recarga el preset al cambiar el .ini: revisá el .sp si usás pit stops."
            )
    return warnings
