"""Launcher for Ingeniero (dev + PyInstaller)."""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Determine base directories.
if getattr(sys, "frozen", False):
    # PyInstaller bundle: resources live in _MEIPASS.
    BUNDLE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    APP_DIR = BUNDLE_DIR

# Make sure the backend package is importable.
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Point config at the right places via env vars before importing app.
os.environ.setdefault("AC_INSTALL", os.environ.get("AC_INSTALL", ""))
os.environ.setdefault("AC_DOCUMENTS", os.environ.get("AC_DOCUMENTS", ""))

import uvicorn

from app import config

# Override config paths for packaged mode: frontend dist and data next to the exe.
if getattr(sys, "frozen", False):
    config.FRONTEND_DIST = BUNDLE_DIR / "frontend" / "dist"
    config.DATA_DIR = APP_DIR / "data"
    config.CACHE_DIR = config.DATA_DIR / "cache"
    config.DB_PATH = config.DATA_DIR / "ingeniero.db"
    config.CATALOG_PATH = config.DATA_DIR / "catalog.json"

HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    config.ensure_dirs()
    # Open browser after a short delay.
    def open_browser():
        time.sleep(2.5)
        webbrowser.open(f"http://{HOST}:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
