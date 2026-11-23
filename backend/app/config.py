from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "ingeniero.db"
CATALOG_PATH = DATA_DIR / "catalog.json"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

AC_ENV = "AC_INSTALL"
DEFAULT_AC_PATHS = [
    Path(r"C:\Program Files (x86)\Steam\steamapps\common\assettocorsa"),
    Path(r"C:\Program Files\Steam\steamapps\common\assettocorsa"),
    Path(r"D:\SteamLibrary\steamapps\common\assettocorsa"),
    Path(r"E:\SteamLibrary\steamapps\common\assettocorsa"),
]

DOCS_ENV = "AC_DOCUMENTS"
DEFAULT_DOC_PATHS = [
    Path.home() / "Documentos" / "Assetto Corsa",
    Path.home() / "Documents" / "Assetto Corsa",
    Path.home() / "OneDrive" / "Documentos" / "Assetto Corsa",
    Path.home() / "OneDrive" / "Documents" / "Assetto Corsa",
]


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def ac_install() -> Path:
    env = os.environ.get(AC_ENV)
    if env and Path(env).exists():
        return Path(env)
    found = _first_existing(DEFAULT_AC_PATHS)
    if found is None:
        raise RuntimeError("No se encontró Assetto Corsa. Definí AC_INSTALL.")
    return found


def ac_documents() -> Path:
    env = os.environ.get(DOCS_ENV)
    if env and Path(env).exists():
        return Path(env)
    found = _first_existing(DEFAULT_DOC_PATHS)
    if found is None:
        raise RuntimeError("No se encontró la carpeta Documentos/Assetto Corsa. Definí AC_DOCUMENTS.")
    return found


def setups_dir() -> Path:
    return ac_documents() / "setups"


def cars_dir() -> Path:
    return ac_install() / "content" / "cars"


def tracks_dir() -> Path:
    return ac_install() / "content" / "tracks"


def ensure_dirs() -> None:
    for path in (DATA_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)
