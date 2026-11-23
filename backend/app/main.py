from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import catalog, config, store
from app.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    store.ensure_db()
    try:
        if not config.CATALOG_PATH.exists():
            catalog.build_catalog()
    except Exception:
        # The API still works if scanning fails; endpoints report the error.
        pass
    yield


app = FastAPI(title="Ingeniero", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/")
    def index() -> dict:
        return {
            "app": "Ingeniero",
            "status": "backend listo",
            "docs": "/docs",
            "frontend": "todavía no compilado (ejecutá npm run build en frontend)",
        }
