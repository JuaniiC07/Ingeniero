from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.car_profiles import classify_car, read_car_info
from app.setup_io import SetupFile

KNOWN_TRACK_TYPES = {
    "spa": "fast",
    "spatw": "fast",
    "monza": "fast",
    "monza tw": "fast",
    "ks_monza66": "fast",
    "rt_daytona": "oval",
    "daytona_2017": "oval",
    "nov_daytona_endurance": "oval",
    "rt_bathurst": "bumpy",
    "ks_nurburgring": "bumpy",
    "fn_nurburgring": "bumpy",
    "nov_nurburgring": "bumpy",
    "macau": "street",
    "monaco": "street",
    "ks_monaco": "street",
    "watkins": "fast",
    "sebring": "bumpy",
    "road_america": "fast",
    "interlagos": "technical",
    "brands_hatch": "technical",
    "donington": "technical",
    "silverstone": "fast",
    "paul_ricard": "fast",
    "le_mans": "fast",
    "lemans": "fast",
    "mount_panorama": "bumpy",
    "nordschleife": "bumpy",
}

TYPE_LABELS = {
    "fast": "Rápido / alta velocidad",
    "technical": "Técnico / curves lentas",
    "bumpy": "Bumpy / desniveles",
    "street": "Calle / muros",
    "oval": "Óvalo",
    "balanced": "Mixto",
}

TRACK_TYPE_HINTS = {
    "fast": ("high speed", "fast", "long straight", "top speed"),
    "bumpy": ("bumpy", "elevation", "crest", "mountain", "kerb"),
    "street": ("street circuit", "public road", "walls", "narrow"),
    "oval": ("oval", "speedway", "banking"),
    "technical": ("technical", "tight", "slow corners", "twisty"),
}


def parse_length_m(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    number = float(match.group(1))
    if "km" in text:
        return number * 1000
    if "mi" in text:
        return number * 1609.34
    return number


def infer_track_type(track_id: str, name: str, tags: list[str], length_m: float | None) -> str:
    key = track_id.lower()
    if key in KNOWN_TRACK_TYPES:
        return KNOWN_TRACK_TYPES[key]
    for known, kind in KNOWN_TRACK_TYPES.items():
        if known in key or known in name.lower():
            return kind
    haystack = f"{name} {' '.join(tags)}".lower()
    for kind, hints in TRACK_TYPE_HINTS.items():
        if any(hint in haystack for hint in hints):
            return kind
    if length_m is not None:
        if length_m > 5500:
            return "fast"
        if length_m < 3500:
            return "technical"
    return "balanced"


def read_track_info(track_id: str) -> dict:
    directory = config.tracks_dir() / track_id
    info = {
        "track_id": track_id,
        "name": track_id,
        "length_m": None,
        "tags": [],
        "country": "",
        "city": "",
        "run": "",
        "pitboxes": None,
    }
    ui = directory / "ui" / "ui_track.json"
    if ui.exists():
        try:
            raw = json.loads(ui.read_text(encoding="utf-8-sig", errors="replace"))
            info["name"] = raw.get("name") or track_id
            info["tags"] = list(raw.get("tags") or [])
            info["country"] = raw.get("country") or ""
            info["city"] = raw.get("city") or ""
            info["run"] = raw.get("run") or ""
            info["length_m"] = parse_length_m(raw.get("length"))
            try:
                info["pitboxes"] = int(raw.get("pitboxes")) if raw.get("pitboxes") else None
            except (TypeError, ValueError):
                pass
        except Exception:
            pass
    info["type"] = infer_track_type(track_id, info["name"], info["tags"], info["length_m"])
    info["type_label"] = TYPE_LABELS.get(info["type"], info["type"])
    return info


def load_personal_bests() -> dict[str, int]:
    path = config.ac_documents() / "personalbest.ini"
    if not path.exists():
        return {}
    out: dict[str, int] = {}
    current = None
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().upper()
            continue
        if current and line.upper().startswith("TIME="):
            try:
                out[current] = int(float(line.split("=", 1)[1].strip()))
            except ValueError:
                pass
    return out


def _lap_for(car_id: str, track_folder: str, bests: dict[str, int]) -> int | None:
    car = car_id.upper()
    track = track_folder.upper()
    candidates: list[int] = []
    for key, value in bests.items():
        if not key.startswith(car + "@"):
            continue
        key_track = key.split("@", 1)[1]
        if key_track == track or key_track.startswith(track + "-"):
            candidates.append(value)
    return min(candidates) if candidates else None


def scan_cars() -> list[dict]:
    cars: list[dict] = []
    base = config.cars_dir()
    if not base.exists():
        return cars
    for directory in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not directory.is_dir():
            continue
        info = read_car_info(directory.name)
        car_class = classify_car(info)
        cars.append(
            {
                "car_id": directory.name,
                "name": info["name"],
                "brand": info["brand"],
                "class": info["class"],
                "car_class": car_class,
                "tags": info["tags"],
                "has_data_folder": info["has_data_folder"],
                "has_data_acd": info["has_data_acd"],
                "has_profile": info["has_data_folder"] or info["has_data_acd"],
            }
        )
    return cars


def scan_tracks() -> list[dict]:
    tracks: list[dict] = []
    base = config.tracks_dir()
    if not base.exists():
        return tracks
    for directory in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not directory.is_dir():
            continue
        tracks.append(read_track_info(directory.name))
    return tracks


def scan_setups(bests: dict[str, int] | None = None) -> list[dict]:
    bests = bests if bests is not None else load_personal_bests()
    setups: list[dict] = []
    base = config.setups_dir()
    if not base.exists():
        return setups
    for car_dir in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not car_dir.is_dir():
            continue
        for track_dir in sorted(car_dir.iterdir(), key=lambda p: p.name.lower()):
            if not track_dir.is_dir():
                continue
            for path in sorted(track_dir.glob("*.ini"), key=lambda p: p.name.lower()):
                try:
                    stat = path.stat()
                except OSError:
                    continue
                setups.append(
                    {
                        "id": f"{car_dir.name}/{track_dir.name}/{path.stem}",
                        "car_id": car_dir.name,
                        "track_id": track_dir.name,
                        "name": path.stem,
                        "file_name": path.name,
                        "path": str(path),
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "size": stat.st_size,
                        "generated": path.stem.upper().startswith("ENG_"),
                        "lap_ms": _lap_for(car_dir.name, track_dir.name, bests),
                    }
                )
    return setups


def build_catalog() -> dict:
    bests = load_personal_bests()
    cars = scan_cars()
    tracks = scan_tracks()
    setups = scan_setups(bests)
    setups_by_car: dict[str, int] = {}
    for setup in setups:
        setups_by_car[setup["car_id"]] = setups_by_car.get(setup["car_id"], 0) + 1
    for car in cars:
        car["saved_setups"] = setups_by_car.get(car["car_id"], 0)
    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ac_install": str(config.ac_install()),
        "documents": str(config.ac_documents()),
        "cars": cars,
        "tracks": tracks,
        "setups": setups,
        "counts": {"cars": len(cars), "tracks": len(tracks), "setups": len(setups)},
    }
    config.ensure_dirs()
    config.CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def load_catalog(force: bool = False) -> dict:
    if not force and config.CATALOG_PATH.exists():
        try:
            return json.loads(config.CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return build_catalog()


def setup_by_id(setup_id: str) -> dict | None:
    catalog = load_catalog()
    for setup in catalog.get("setups", []):
        if setup["id"] == setup_id:
            return setup
    return None


def parse_setup_file(path: Path) -> dict:
    setup = SetupFile.from_path(path)
    return {"text": setup.text, "values": setup.to_dict()}
