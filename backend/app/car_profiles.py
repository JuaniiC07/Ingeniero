from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache, reduce
from math import gcd
from pathlib import Path

import acd

from app import config
from app.ini_utils import SpecParam, as_float, parse_sections
from app.setup_io import SetupFile, format_number

TAB_ORDER = [
    "TYRES",
    "ALIGNMENT",
    "SUSPENSION",
    "SUSPENSIONS",
    "DAMPERS",
    "AERO",
    "DRIVETRAIN",
    "BRAKES",
    "GENERIC",
    "BUMPSTOP",
    "VISUALES",
    "OTHER",
]

# Default units per parameter family. The unit is only used when the game
# shows the raw value (SHOW_CLICKS=0); click-based parameters are labelled
# "click" because that is exactly what Assetto Corsa displays.
SECTION_UNITS = {
    "PRESSURE_": ("psi", 0),
    "CAMBER_": ("°", 1),
    "TOE_OUT_": ("", 0),
    "CASTER_": ("°", 1),
    "SPRING_RATE_": ("N/mm", 0),
    "ARB_": ("N/m", 0),
    "DAMP_FAST_": ("Ns/m", 0),
    "DAMP_": ("Ns/m", 0),
    "ROD_LENGTH_": ("mm", 0),
    "PACKER_RANGE_": ("mm", 0),
    "BUMPSTOP_": ("nivel", 0),
    "BUMP_STOP_RATE_": ("nivel", 0),
    "DIFF_PRELOAD": ("Nm", 0),
    "DIFF_POWER": ("%", 0),
    "DIFF_COAST": ("%", 0),
    "FRONT_BIAS": ("%", 0),
    "BRAKE_POWER_MULT": ("%", 0),
    "BRAKE_DUCT_": ("%", 0),
    "FUEL": ("L", 1),
    "WING_": ("paso", 0),
    "ABS": ("nivel", 0),
    "TRACTION_CONTROL": ("nivel", 0),
    "STEER_ASSIST": ("%", 0),
    "FINAL_RATIO": ("paso", 0),
    "INTERNAL_GEAR_": ("paso", 0),
    "TYRES": ("compuesto", 0),
}

# Display steps used when the car does not declare a trustworthy STEP.
DEFAULT_DISPLAY_STEP = {
    "CAMBER_": 0.1,
    "TOE_OUT_": 0.01,
    "CASTER_": 0.1,
    "PRESSURE_": 1.0,
    "ROD_LENGTH_": 1.0,
    "PACKER_RANGE_": 1.0,
    "BUMPSTOP_": 1.0,
    "BUMP_STOP_RATE_": 1.0,
    "DIFF_PRELOAD": 10.0,
    "DIFF_POWER": 5.0,
    "DIFF_COAST": 5.0,
    "FRONT_BIAS": 1.0,
    "FUEL": 1.0,
    "WING_": 1.0,
    "ABS": 1.0,
    "TRACTION_CONTROL": 1.0,
    "BRAKE_DUCT_": 10.0,
    "STEER_ASSIST": 1.0,
    "FINAL_RATIO": 1.0,
    "INTERNAL_GEAR_": 1.0,
    "TYRES": 1.0,
}

# Sections that are metadata or CSP internals, never setup parameters.
SKIP_SECTIONS = {"ABOUT", "CAR", "HEADER", "__EXT_PATCH"}
SKIP_PREFIXES = ("CUSTOM_SCRIPT_ITEM_",)

CAR_CLASS_ALIASES = {
    "gt3": "gt3",
    "gt2": "gt3",
    "gt4": "gt3",
    "gt": "gt3",
    "formula": "formula",
    "f1": "formula",
    "f2": "formula",
    "f3": "formula",
    "formula 1": "formula",
    "prototype": "formula",
    "lmp": "formula",
    "oreca": "formula",
}


def _section_meta(section: str) -> tuple[str, int]:
    upper = section.upper()
    for prefix, meta in SECTION_UNITS.items():
        if upper == prefix.rstrip("_") or upper.startswith(prefix):
            return meta
    return ("", 0)


def _default_display_step(section: str) -> float | None:
    upper = section.upper()
    for prefix, step in DEFAULT_DISPLAY_STEP.items():
        if upper == prefix.rstrip("_") or upper.startswith(prefix):
            return step
    return None


@dataclass
class SavedSetupValues:
    path: Path
    track_folder: str
    values: dict[str, float]
    file_name: str


@dataclass
class ParamProfile:
    section: str
    label: str
    tab: str
    unit: str
    mode: str
    scale: float
    step: float
    minimum: float
    maximum: float
    current: float
    decimals: int
    has_value: bool
    show_clicks: int
    help: str = ""
    note: str = ""
    div: float = 1.0
    offset: float = 0.0

    def display(self, internal: float | None = None) -> float:
        value = self.current if internal is None else internal
        if not self.div:
            return value
        return (value - self.offset) / self.div

    def to_internal(self, display_value: float) -> float:
        return display_value * self.div + self.offset

    def to_file(self, internal: float) -> str:
        if self.mode.startswith("clicks") or abs(internal - round(internal)) < 1e-6:
            return format_number(float(round(internal)), 0)
        return format_number(internal, 3)

    def step_display(self) -> float:
        return self.step / self.div if self.div else self.step

    def range_display(self) -> tuple[float, float]:
        if not self.div:
            return (self.minimum, self.maximum)
        return ((self.minimum - self.offset) / self.div, (self.maximum - self.offset) / self.div)

    def to_dict(self) -> dict:
        lo, hi = self.range_display()
        return {
            "section": self.section,
            "label": self.label,
            "tab": self.tab,
            "unit": self.unit,
            "mode": self.mode,
            "display": round(self.display(), 4),
            "current": round(self.current, 4),
            "minimum": round(self.minimum, 4),
            "maximum": round(self.maximum, 4),
            "min_display": round(lo, 4),
            "max_display": round(hi, 4),
            "step_display": round(self.step_display(), 4),
            "step": round(self.step, 4),
            "decimals": self.decimals,
            "has_value": self.has_value,
            "show_clicks": self.show_clicks,
            "note": self.note,
            "help": self.help,
        }


@dataclass
class CarProfile:
    car_id: str
    name: str
    brand: str
    car_class: str
    tags: list[str]
    spec_source: str
    spec_available: bool
    saved_setups: int
    warnings: list[str]
    params: list[ParamProfile]

    def by_section(self) -> dict[str, ParamProfile]:
        return {p.section: p for p in self.params}

    def groups(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for param in self.params:
            tab = param.tab if param.tab in TAB_ORDER else "OTHER"
            groups.setdefault(tab, []).append(param.to_dict())
        return {tab: groups[tab] for tab in TAB_ORDER if tab in groups}

    def to_dict(self) -> dict:
        return {
            "car_id": self.car_id,
            "name": self.name,
            "brand": self.brand,
            "car_class": self.car_class,
            "tags": self.tags,
            "spec_source": self.spec_source,
            "spec_available": self.spec_available,
            "saved_setups": self.saved_setups,
            "warnings": self.warnings,
            "params": [p.to_dict() for p in self.params],
            "groups": self.groups(),
        }


def car_dir(car_id: str) -> Path:
    return config.cars_dir() / car_id


def read_car_info(car_id: str) -> dict:
    directory = car_dir(car_id)
    info = {
        "car_id": car_id,
        "name": car_id,
        "brand": "",
        "class": "race",
        "tags": [],
        "has_data_folder": (directory / "data" / "setup.ini").exists(),
        "has_data_acd": (directory / "data.acd").exists(),
    }
    ui = directory / "ui" / "ui_car.json"
    if ui.exists():
        try:
            raw = json.loads(ui.read_text(encoding="utf-8-sig", errors="replace"))
            info["name"] = raw.get("name") or car_id
            info["brand"] = raw.get("brand") or ""
            info["class"] = raw.get("class") or "race"
            info["tags"] = list(raw.get("tags") or [])
        except Exception:
            pass
    return info


def classify_car(info: dict) -> str:
    haystack = " ".join(
        [str(info.get("name", "")), str(info.get("class", "")), " ".join(info.get("tags", []))]
    ).lower()
    if "gt3" in haystack or "gt4" in haystack or "gt2" in haystack:
        return "gt3"
    for alias, car_class in CAR_CLASS_ALIASES.items():
        if alias in haystack:
            return car_class
    if info.get("class") == "race":
        return "race"
    if "drift" in haystack:
        return "drift"
    return "road"


@lru_cache(maxsize=512)
def _read_spec_text(car_id: str, marker: float) -> tuple[str | None, str]:
    directory = car_dir(car_id)
    unpacked = directory / "data" / "setup.ini"
    if unpacked.exists():
        return unpacked.read_text(encoding="utf-8-sig", errors="replace"), "data/setup.ini"
    packed = directory / "data.acd"
    if packed.exists():
        try:
            items = acd.read_bytes(packed.read_bytes(), acd.new_crypt_key(directory.name))
            raw = items.get("setup.ini")
            if raw:
                text = raw.decode("utf-8-sig", errors="replace")
                cache = config.CACHE_DIR / f"{car_id}.setup.ini"
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(text, encoding="utf-8")
                return text, "data.acd"
        except Exception:
            return None, "none"
    return None, "none"


def read_spec_text(car_id: str) -> tuple[str | None, str]:
    directory = car_dir(car_id)
    marker = 0.0
    for candidate in (directory / "data" / "setup.ini", directory / "data.acd"):
        if candidate.exists():
            marker = max(marker, candidate.stat().st_mtime)
    return _read_spec_text(car_id, marker)


def parse_spec(car_id: str) -> tuple[dict[str, SpecParam], str]:
    text, source = read_spec_text(car_id)
    if not text:
        return {}, source
    sections = parse_sections(text)
    display_method = sections.get("DISPLAY_METHOD", {})
    global_clicks = int(as_float(display_method.get("SHOW_CLICKS")) or 0)
    specs: dict[str, SpecParam] = {}
    for section, values in sections.items():
        if section in SKIP_SECTIONS or section.startswith(SKIP_PREFIXES):
            continue
        if not any(key in values for key in ("NAME", "MIN", "MAX", "LUT", "RATIOS")):
            continue
        raw_clicks = values.get("SHOW_CLICKS")
        specs[section] = SpecParam(
            section=section,
            name=values.get("NAME", section.replace("_", " ").title()),
            tab=values.get("TAB", "OTHER").upper(),
            minimum=as_float(values.get("MIN")),
            maximum=as_float(values.get("MAX")),
            step=as_float(values.get("STEP")),
            show_clicks=int(as_float(raw_clicks)) if raw_clicks is not None else global_clicks,
            help=values.get("HELP", ""),
            lut=values.get("LUT") or values.get("RATIOS"),
            raw=values,
        )
    return specs, source


def _round_sig(value: float) -> float:
    if value == 0:
        return 0.0
    return float(f"{value:.6g}")


def _infer_mode(values: list[float], spec: SpecParam | None) -> tuple[str, float]:
    """Infer how the saved file relates to the declared MIN/MAX range."""
    if not values:
        return "observed", 1.0
    if spec and spec.minimum is not None and spec.maximum is not None:
        lo, hi = sorted((spec.minimum, spec.maximum))
        eps = max(abs(hi - lo) * 1e-6, 1e-6)
        if all(lo - eps <= value <= hi + eps for value in values):
            return "physical", 1.0
        for factor in (10.0, 100.0):
            if all(lo - eps <= value / factor <= hi + eps for value in values):
                return "scaled", factor
        if spec.step and spec.step > 0:
            clicks = round((hi - lo) / spec.step)
            if 0 < clicks <= 300 and all(-eps <= value <= clicks + eps for value in values):
                return "clicks", 1.0
        return "relative", 1.0
    return "observed", 1.0


def _gcd_step(values: list[float], declared: float) -> float:
    """Smallest step that explains the observed saved values.

    Mods are often inconsistent: a car may declare STEP=10 but store 6, 9 and
    12. The greatest common divisor of the observed differences recovers the
    real grid without inventing values, and we never go above the declared
    step.
    """
    distinct = sorted({round(value, 6) for value in values})
    diffs = [b - a for a, b in zip(distinct, distinct[1:]) if b - a > 1e-9]
    if not diffs:
        return declared
    scaled = [max(1, int(round(diff * 1000))) for diff in diffs]
    g = reduce(gcd, scaled) / 1000.0
    if g <= 0:
        return declared
    return min(g, declared) if declared and declared > 0 else g


def _is_aligned(value: float, anchor: float, step: float) -> bool:
    if step <= 0:
        return True
    ratio = (value - anchor) / step
    return abs(ratio - round(ratio)) < 1e-6


def load_saved_setups(car_id: str) -> list[SavedSetupValues]:
    base = config.setups_dir() / car_id
    if not base.exists():
        return []
    out: list[SavedSetupValues] = []
    for path in sorted(base.rglob("*.ini")):
        if path.name.lower().startswith("eng_"):
            continue
        try:
            setup = SetupFile.from_path(path)
            values = setup.numeric()
        except Exception:
            continue
        if values:
            out.append(
                SavedSetupValues(
                    path=path,
                    track_folder=path.parent.name,
                    values=values,
                    file_name=path.stem,
                )
            )
    return out


def _build_profile(
    car_id: str,
    setup: SetupFile,
    specs: dict[str, SpecParam],
    saved: list[SavedSetupValues],
    source: str,
) -> CarProfile:
    info = read_car_info(car_id)
    car_class = classify_car(info)
    warnings: list[str] = []
    if source == "none":
        warnings.append("El coche no tiene data/setup.ini ni data.acd legible: perfil inferido de tus setups.")
    if not saved:
        warnings.append("No hay setups guardados de este coche: los límites salen solo del setup.ini.")

    current_values = setup.numeric()
    observed: dict[str, list[float]] = {}
    for entry in saved:
        for section, value in entry.values.items():
            observed.setdefault(section, []).append(value)

    profiles: list[ParamProfile] = []
    sections = set(specs) | set(current_values) | set(observed)
    for section in sections:
        if section in SKIP_SECTIONS or section.startswith(SKIP_PREFIXES):
            continue
        spec = specs.get(section)
        current = current_values.get(section)
        values = list(observed.get(section, []))
        if current is not None:
            values.append(current)
        if current is None and not values:
            continue
        if current is None:
            current = values[0]

        mode, scale = _infer_mode(values, spec)
        unit, decimals = _section_meta(section)
        label = spec.name if spec and spec.name else section.replace("_", " ").title()
        show = spec.show_clicks if spec else 0
        declared_min = spec.minimum if spec else None
        declared_max = spec.maximum if spec else None
        declared_step = spec.step if spec and spec.step and spec.step > 0 else None

        div = 1.0
        offset = 0.0
        click_mode: str | None = None

        # Assetto Corsa's own setup.ini documents SHOW_CLICKS:
        #   0 = actual value, 1 = clicks from MIN, 2 = clicks from 0.
        if declared_min is not None and declared_max is not None and declared_step:
            lo_d, hi_d = sorted((declared_min, declared_max))
            eps = max(abs(hi_d - lo_d) * 1e-6, 1e-6)
            in_declared = all(lo_d - eps <= value <= hi_d + eps for value in values)
            if show == 2 and (
                in_declared
                or all(
                    lo_d / declared_step - eps <= value / declared_step <= hi_d / declared_step + eps
                    for value in values
                )
            ):
                click_mode = "clicks2"
                div = declared_step
                offset = 0.0
            elif show == 1 and (
                in_declared
                or all(
                    -eps <= (value - lo_d) / declared_step <= (hi_d - lo_d) / declared_step + eps
                    for value in values
                )
            ):
                click_mode = "clicks1"
                div = declared_step
                offset = lo_d

        if click_mode:
            unit = "click"
            decimals = 1
        elif mode == "scaled":
            div = scale
            offset = 0.0
        elif mode == "clicks":
            unit = "click"
            decimals = 0
            div = 1.0
            offset = 0.0
        elif section.startswith("TOE_OUT_"):
            # Without click display we cannot be sure of the physical unit.
            unit = ""
            decimals = 0

        # Internal (file) range.
        note = ""
        if click_mode or mode in ("physical", "scaled", "clicks"):
            if declared_min is not None and declared_max is not None:
                lo_i, hi_i = sorted((declared_min, declared_max))
                if mode == "scaled" and not click_mode:
                    lo_i, hi_i = lo_i * scale, hi_i * scale
                elif mode == "clicks" and not click_mode and declared_step:
                    n = round((hi_i - lo_i) / declared_step)
                    lo_i, hi_i = 0.0, float(max(n, 0))
                    note = f"El coche usa clicks ({n} posiciones)."
            else:
                lo_i, hi_i = min(values), max(values)
        else:
            step_guess = declared_step or 1.0
            lo_i = min(values) - step_guess if values else current - step_guess
            hi_i = max(values) + step_guess if values else current + step_guess
            if values and min(values) >= 0:
                lo_i = max(0.0, lo_i)
            if declared_min is not None and declared_max is not None:
                slo, shi = sorted((declared_min, declared_max))
                lo_i, hi_i = min(lo_i, slo), max(hi_i, shi)
            if hi_i - lo_i < step_guess:
                lo_i, hi_i = current - step_guess, current + step_guess
            note = "Unidades relativas: los cambios se hacen en pasos pequeños alrededor del valor actual."

        if mode == "scaled" and not click_mode:
            note = f"Escala del coche: {format_number(scale, 0)} unidades internas por unidad mostrada."

        if current < lo_i:
            lo_i = current
            note = (note + " " if note else "") + "El setup guardado está por debajo del mínimo declarado; se amplió el límite."
        elif current > hi_i:
            hi_i = current
            note = (note + " " if note else "") + "El setup guardado supera el máximo declarado; se amplió el límite."

        # Internal step.
        if click_mode:
            step_i = declared_step or 1.0
        elif mode == "scaled":
            display_step = _default_display_step(section)
            if display_step is None:
                display_step = (declared_step / scale) if declared_step else 1.0
            step_i = display_step * scale
        elif mode == "physical":
            step_i = declared_step or (_default_display_step(section) or 1.0)
        elif mode == "clicks":
            step_i = 1.0
        else:
            step_i = declared_step or 1.0

        # If the saved value does not sit on the declared grid, fall back to the
        # step that the saved setups actually use.
        anchor = 0.0 if click_mode == "clicks2" else lo_i
        if mode in ("physical", "scaled") or click_mode:
            if not _is_aligned(current, anchor, step_i):
                gcd_step = _gcd_step(values, step_i)
                if 1e-9 < gcd_step < step_i:
                    shown_step = gcd_step / div if div else gcd_step
                    shown_unit = "click" if click_mode else unit
                    note = (
                        (note + " " if note else "")
                        + f"Tu setup no sigue la grilla declarada; los ajustes se hacen en pasos de {format_number(shown_step, 3)} {shown_unit}".rstrip()
                        + "."
                    )
                    step_i = gcd_step

        profiles.append(
            ParamProfile(
                section=section,
                label=label,
                tab=(spec.tab if spec and spec.tab else "OTHER"),
                unit=unit,
                mode=click_mode or mode,
                scale=div,
                step=_round_sig(step_i),
                minimum=_round_sig(lo_i),
                maximum=_round_sig(hi_i),
                current=float(current),
                decimals=decimals,
                has_value=section in current_values,
                show_clicks=show,
                help=spec.help if spec else "",
                note=note,
                div=div,
                offset=offset,
            )
        )

    def sort_key(param: ParamProfile) -> tuple[int, str]:
        tab = param.tab if param.tab in TAB_ORDER else "OTHER"
        return (TAB_ORDER.index(tab), param.section)

    profiles.sort(key=sort_key)
    missing = [section for section in current_values if section not in {p.section for p in profiles}]
    if missing:
        warnings.append(f"Secciones no interpretadas: {', '.join(missing[:6])}")
    return CarProfile(
        car_id=car_id,
        name=info["name"],
        brand=info["brand"],
        car_class=car_class,
        tags=info["tags"],
        spec_source=source,
        spec_available=source in ("data/setup.ini", "data.acd"),
        saved_setups=len(saved),
        warnings=warnings,
        params=profiles,
    )


def build_profile(car_id: str, setup: SetupFile) -> CarProfile:
    specs, source = parse_spec(car_id)
    saved = load_saved_setups(car_id)
    return _build_profile(car_id, setup, specs, saved, source)


def find_setup_paths(car_id: str) -> list[Path]:
    base = config.setups_dir() / car_id
    if not base.exists():
        return []
    return sorted(base.rglob("*.ini"))
