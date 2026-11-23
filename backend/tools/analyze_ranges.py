"""Focused analysis of saved setups vs setup.ini limits for a few key params."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import acd

AC = Path(r"C:\Program Files (x86)\Steam\steamapps\common\assettocorsa")
CARS = AC / "content" / "cars"
SETUPS = Path.home() / "Documentos" / "Assetto Corsa" / "setups"
KEYS = {
    "ARB_FRONT", "ARB_REAR", "ARB_F", "ARB_R", "CAMBER_LF", "CAMBER_RF",
    "CAMBER_LR", "CAMBER_RR", "TOE_OUT_LF", "TOE_OUT_RF", "TOE_OUT_LR",
    "TOE_OUT_RR", "ROD_LENGTH_LF", "ROD_LENGTH_RF", "ROD_LENGTH_LR",
    "ROD_LENGTH_RR", "SPRING_RATE_LF", "SPRING_RATE_LR", "DIFF_PRELOAD",
    "FRONT_BIAS", "PRESSURE_LF", "PRESSURE_LR", "WING_2", "WING_3",
}
SECTION_RE = re.compile(r"^\[([^\]]+)\]")


def parse_ini(text: str) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "//", "#")):
            continue
        m = SECTION_RE.match(line)
        if m:
            current = data.setdefault(m.group(1).strip().upper(), {})
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip().upper()] = value.split(";", 1)[0].strip()
    return data


def car_setup_ini(car_dir: Path) -> str | None:
    unpacked = car_dir / "data" / "setup.ini"
    if unpacked.exists():
        return unpacked.read_text(encoding="utf-8", errors="replace")
    packed = car_dir / "data.acd"
    if packed.exists():
        try:
            items = acd.read_bytes(packed.read_bytes(), acd.new_crypt_key(car_dir.name))
            raw = items.get("setup.ini")
            if raw:
                return raw.decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            print(f"! acd {car_dir.name}: {exc}")
    return None


def main() -> None:
    rows = []
    car_names = {p.name for p in CARS.iterdir() if p.is_dir()}
    for car_dir in [p for p in SETUPS.iterdir() if p.is_dir() and p.name in car_names]:
        text = car_setup_ini(CARS / car_dir.name)
        if not text:
            continue
        spec = parse_ini(text)
        for setup_file in car_dir.rglob("*.ini"):
            setup = parse_ini(setup_file.read_text(encoding="utf-8", errors="replace"))
            for section, values in setup.items():
                if section not in KEYS or "VALUE" not in values or section not in spec:
                    continue
                declared = spec[section]
                if "MIN" not in declared or "MAX" not in declared:
                    continue
                try:
                    v = float(values["VALUE"])
                    lo, hi = sorted((float(declared["MIN"]), float(declared["MAX"])))
                except ValueError:
                    continue
                if lo <= v <= hi:
                    continue
                rows.append((section, car_dir.name, setup_file.parent.name, v, lo, hi, declared.get("STEP"), declared.get("SHOW_CLICKS")))

    by_section = Counter(r[0] for r in rows)
    print("out-of-range by section:", dict(by_section))
    seen = set()
    for section, car, track, v, lo, hi, step, clicks in rows:
        key = (section, car, v)
        if key in seen:
            continue
        seen.add(key)
        print(f"{section:16s} {car:32s} {track:12s} value={v:>8} range={lo:>7}..{hi:<7} step={step} clicks={clicks}")


if __name__ == "__main__":
    main()
