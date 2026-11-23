"""Exploratory tool: compare saved AC setups against each car's setup.ini limits.

Reads data/setup.ini from the car folder when unpacked, otherwise decrypts
data.acd with acd.py (key = car folder name). Prints which scale factor makes
saved values fit the declared MIN/MAX range.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import acd

AC = Path(r"C:\Program Files (x86)\Steam\steamapps\common\assettocorsa")
CARS = AC / "content" / "cars"
SETUPS = Path.home() / "Documentos" / "Assetto Corsa" / "setups"

SECTION_RE = re.compile(r"^\[([^\]]+)\]")


def parse_ini(text: str) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
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
        value = value.split(";", 1)[0].strip()
        current[key.strip().upper()] = value
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
            print(f"  ! acd failed for {car_dir.name}: {exc}")
    return None


def main() -> None:
    fit_counts: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    specs_out = {}

    car_names = {p.name for p in CARS.iterdir() if p.is_dir()}
    saved_cars = [p for p in SETUPS.iterdir() if p.is_dir() and p.name in car_names]
    print(f"cars with saved setups: {len(saved_cars)}")

    for car_dir in saved_cars:
        text = car_setup_ini(CARS / car_dir.name)
        if text is None:
            print(f"- skip {car_dir.name}: no setup.ini")
            continue
        spec = parse_ini(text)
        specs_out[car_dir.name] = spec
        for setup_file in car_dir.rglob("*.ini"):
            setup = parse_ini(setup_file.read_text(encoding="utf-8", errors="replace"))
            for section, values in setup.items():
                if "VALUE" not in values or section not in spec:
                    continue
                declared = spec[section]
                if "MIN" not in declared or "MAX" not in declared:
                    continue
                try:
                    value = float(values["VALUE"])
                    lo = float(declared["MIN"])
                    hi = float(declared["MAX"])
                except ValueError:
                    continue
                if lo > hi:
                    lo, hi = hi, lo
                if lo <= value <= hi:
                    fit_counts[section]["x1"] += 1
                else:
                    for factor, label in ((10, "/10"), (100, "/100"), (0.1, "x10"), (0.01, "x100")):
                        scaled = value / factor if factor >= 1 else value * factor
                        if lo <= scaled <= hi:
                            fit_counts[section][label] += 1
                            if len(examples[section]) < 4:
                                examples[section].append(
                                    f"{car_dir.name}/{setup_file.parent.name}: {section}={value} "
                                    f"range={lo}..{hi} fits {label}"
                                )
                            break
                    else:
                        fit_counts[section]["NONE"] += 1
                        if len(examples[section]) < 4:
                            examples[section].append(
                                f"{car_dir.name}/{setup_file.parent.name}: {section}={value} "
                                f"range={lo}..{hi} NO FIT"
                            )

    for section in sorted(fit_counts):
        print(f"{section:22s} {dict(fit_counts[section])}")
    print("\nExamples for non-x1:")
    for section, rows in examples.items():
        print(f"\n[{section}]")
        for row in rows:
            print("  " + row)

    out = Path(r"C:\Users\juanm\AppData\Local\Temp\opencode\ac_setup_specs.json")
    out.write_text(json.dumps(specs_out, indent=2), encoding="utf-8")
    print(f"\nspecs written to {out}")


if __name__ == "__main__":
    main()
