from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app import catalog, config, llm, store
from app.pit_preset import check as check_pit_preset
from app.ac_live import read_live
from app.car_profiles import build_profile, car_dir
from app.catalog import infer_track_type, load_catalog, read_track_info
from app.engine import analyze
from app.ini_utils import parse_sections
from app.schemas import (
    AnalyzeRequest,
    InspectRequest,
    LlmNarrateRequest,
    ResultRequest,
    SaveRequest,
    SessionCreate,
    SessionUpdate,
)
from app.setup_io import SetupFile

router = APIRouter(prefix="/api")


def _catalog_car(car_id: str) -> dict | None:
    for car in load_catalog().get("cars", []):
        if car["car_id"] == car_id:
            return car
    return None


def _catalog_track(track_id: str) -> dict | None:
    for track in load_catalog().get("tracks", []):
        if track["track_id"] == track_id:
            return track
    return None


def _car_from_text(text: str) -> str | None:
    sections = parse_sections(text)
    model = sections.get("CAR", {}).get("MODEL")
    return model.strip() if model else None


def _resolve_setup_path(raw: str) -> Path:
    base = config.setups_dir().resolve()
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    try:
        path = path.resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Ruta inválida: {exc}") from exc
    if not path.is_relative_to(base):
        raise HTTPException(status_code=400, detail="El setup debe estar dentro de Documentos/Assetto Corsa/setups.")
    if path.suffix.lower() != ".ini":
        raise HTTPException(status_code=400, detail="El archivo debe ser un .ini de Assetto Corsa.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="No se encontró el archivo de setup.")
    return path


def _track_payload(track_id: str | None) -> dict:
    if not track_id:
        return {"track_id": "generic", "name": "Sin circuito", "type": "balanced", "type_label": "Mixto"}
    info = _catalog_track(track_id)
    if info:
        return info
    return read_track_info(track_id)


def _resolve_request(req: AnalyzeRequest) -> tuple[SetupFile, str, str, str, str | None, dict]:
    setup_path: str | None = None
    setup_name = req.setup_name or "import"
    car_id = req.car_id
    track_id = req.track_id

    if req.setup_path:
        path = _resolve_setup_path(req.setup_path)
        setup = SetupFile.from_path(path)
        setup_path = str(path)
        setup_name = req.setup_name or path.stem
        relative = path.relative_to(config.setups_dir().resolve()).parts
        if len(relative) >= 2:
            car_id = car_id or relative[0]
            track_id = track_id or relative[1]
    elif req.setup_text:
        setup = SetupFile.parse(req.setup_text)
        car_id = car_id or _car_from_text(req.setup_text)
    else:
        raise HTTPException(status_code=400, detail="Enviá setup_path o setup_text.")

    if not car_id:
        raise HTTPException(status_code=400, detail="No pude detectar el coche. Enviá car_id.")
    directory = car_dir(car_id)
    if not directory.exists():
        raise HTTPException(status_code=404, detail=f"No encontré el coche '{car_id}' en content/cars.")
    track_id = track_id or "generic"
    track = _track_payload(track_id)
    return setup, car_id, track_id, setup_name, setup_path, track


def _inspect_response(
    setup: SetupFile, car_id: str, track_id: str, setup_name: str, setup_path: str | None
) -> dict[str, Any]:
    profile = build_profile(car_id, setup)
    track = _track_payload(track_id)
    car = _catalog_car(car_id) or {
        "car_id": car_id,
        "name": profile.name,
        "brand": profile.brand,
        "car_class": profile.car_class,
        "tags": profile.tags,
        "saved_setups": profile.saved_setups,
    }
    warnings = list(profile.warnings)
    warnings.extend(check_pit_preset(setup_path))
    warnings = list(dict.fromkeys(warnings))
    return {
        "setup": {
            "name": setup_name,
            "path": setup_path,
            "text": setup.text,
            "values": setup.to_dict(),
        },
        "car": car,
        "track": track,
        "profile": profile.to_dict(),
        "warnings": warnings,
    }


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "ac_install": str(config.ac_install()),
        "documents": str(config.ac_documents()),
        "llm": llm.status(),
    }


@router.get("/catalog")
def get_catalog(force: bool = False) -> dict:
    return load_catalog(force=force)


@router.post("/catalog/refresh")
def refresh_catalog() -> dict:
    return catalog.build_catalog()


@router.get("/cars/{car_id}/profile")
def car_profile(car_id: str, setup_path: str | None = Query(default=None)) -> dict:
    if not car_dir(car_id).exists():
        raise HTTPException(status_code=404, detail="Coche no encontrado.")
    if setup_path:
        path = _resolve_setup_path(setup_path)
        setup = SetupFile.from_path(path)
    else:
        saved = config.setups_dir() / car_id
        candidates = sorted(saved.rglob("*.ini")) if saved.exists() else []
        if candidates:
            setup = SetupFile.from_path(candidates[-1])
        else:
            empty = "[CAR]\nMODEL=" + car_id + "\n"
            setup = SetupFile.parse(empty)
    profile = build_profile(car_id, setup)
    return profile.to_dict()


@router.get("/setup")
def get_setup(path: str) -> dict:
    resolved = _resolve_setup_path(path)
    setup = SetupFile.from_path(resolved)
    relative = resolved.relative_to(config.setups_dir().resolve()).parts
    car_id = relative[0] if len(relative) >= 2 else _car_from_text(setup.text)
    track_id = relative[1] if len(relative) >= 2 else "generic"
    if not car_id:
        raise HTTPException(status_code=400, detail="No pude detectar el coche del setup.")
    return _inspect_response(setup, car_id, track_id, resolved.stem, str(resolved))


@router.post("/setup/inspect")
def inspect_setup(req: InspectRequest) -> dict:
    setup = SetupFile.parse(req.text)
    car_id = req.car_id or _car_from_text(req.text)
    if not car_id:
        raise HTTPException(status_code=400, detail="No pude detectar el coche. Enviá car_id.")
    if not car_dir(car_id).exists():
        raise HTTPException(status_code=404, detail=f"No encontré '{car_id}' en content/cars.")
    track_id = req.track_id or "generic"
    return _inspect_response(setup, car_id, track_id, req.name or "import", None)


@router.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest) -> dict:
    setup, car_id, track_id, setup_name, setup_path, track = _resolve_request(req)
    result = analyze(
        setup=setup,
        car_id=car_id,
        track_id=track_id,
        setup_name=setup_name,
        setup_path=setup_path,
        track_name=track.get("name") or track_id,
        track_type=req.context.track_type or track.get("type") or infer_track_type(track_id, track.get("name", ""), [], None),
        context=req.context,
        feedback=req.feedback,
        use_llm=req.use_llm,
    )
    result["warnings"] = list(dict.fromkeys([*result.get("warnings", []), *check_pit_preset(setup_path)]))
    result["session_id"] = req.session_id
    analysis_id = store.create_analysis(
        {
            "car_id": car_id,
            "car_name": result["car"]["name"],
            "track_id": track_id,
            "track_name": result["track"]["name"],
            "setup_name": setup_name,
            "setup_path": setup_path,
            "setup_text": setup.text,
            "new_setup_text": result["setup"]["new_text"],
            "context": req.context.model_dump(),
            "feedback": req.feedback.model_dump(),
            "diagnosis": result["diagnosis"],
            "changes": result["changes"],
            "test_plan": result["test_plan"],
            "explanation": result["explanation"],
            "warnings": result["warnings"],
            "session_id": req.session_id,
        }
    )
    result["analysis_id"] = analysis_id
    result["created_at"] = datetime.now().astimezone().isoformat()
    return result


@router.post("/save")
def save_setup(req: SaveRequest) -> dict:
    analysis = store.get_analysis(req.analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    car_id = analysis.get("car_id")
    track_id = analysis.get("track_id") or "generic"
    if analysis.get("saved_path"):
        return {"path": analysis["saved_path"], "already_saved": True}

    safe_name = (req.name or "").strip()
    if not safe_name:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = f"ENG_{stamp}_{analysis.get('setup_name') or 'setup'}"
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", safe_name).strip(" .")
    if not safe_name:
        safe_name = "ENG_setup"
    if safe_name.lower().endswith(".ini"):
        safe_name = safe_name[:-4]

    if analysis.get("setup_path"):
        base_dir = Path(analysis["setup_path"]).parent
    else:
        base_dir = config.setups_dir() / car_id / track_id
    base_dir = base_dir.resolve()
    if not base_dir.is_relative_to(config.setups_dir().resolve()):
        raise HTTPException(status_code=400, detail="Destino inválido.")
    base_dir.mkdir(parents=True, exist_ok=True)

    target = base_dir / f"{safe_name}.ini"
    if target.exists() and not req.overwrite:
        index = 2
        while target.exists():
            target = base_dir / f"{safe_name}_{index}.ini"
            index += 1
    if target.exists() and req.overwrite:
        target.with_suffix(".ini.bak").write_bytes(target.read_bytes())

    text = analysis.get("new_setup_text") or analysis.get("setup_text") or ""
    with open(target, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    store.mark_saved(req.analysis_id, str(target))
    if analysis.get("session_id"):
        try:
            store.link_analysis_to_session(req.analysis_id, int(analysis["session_id"]))
        except Exception:
            pass
    try:
        catalog.build_catalog()
    except Exception:
        pass
    return {"path": str(target), "name": target.stem, "already_saved": False}


@router.post("/result")
def save_result(req: ResultRequest) -> dict:
    analysis = store.get_analysis(req.analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    result = {
        "best_lap_ms": req.best_lap_ms,
        "avg_lap_ms": req.avg_lap_ms,
        "notes": req.notes,
        "outcome": req.outcome,
        "recorded_at": datetime.now().astimezone().isoformat(),
    }
    store.add_result(req.analysis_id, result)
    return {"ok": True, "result": result}


@router.get("/history")
def history(limit: int = 50) -> dict:
    return {"analyses": store.list_analyses(limit=min(max(limit, 1), 200))}


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: int) -> dict:
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    return _analysis_response(analysis)


def _analysis_response(item: dict) -> dict:
    """Normalise a stored analysis to the same shape returned by /analyze."""
    context = item.get("context") or {}
    test_plan = item.get("test_plan") or {
        "baseline_laps": 3,
        "test_laps": context.get("laps_target") or 5,
        "procedure": [],
        "watch": [],
        "success_criteria": "",
        "conditions": "",
    }
    return {
        "analysis_id": item["id"],
        "created_at": item["created_at"],
        "car": {
            "car_id": item.get("car_id"),
            "name": item.get("car_name") or item.get("car_id") or "Coche",
            "brand": "",
            "car_class": "",
            "tags": [],
            "spec_source": "",
            "saved_setups": 0,
        },
        "track": {
            "track_id": item.get("track_id") or "generic",
            "name": item.get("track_name") or item.get("track_id") or "Sin circuito",
            "type": context.get("track_type") or "balanced",
        },
        "setup": {
            "name": item.get("setup_name") or "setup",
            "path": item.get("setup_path"),
            "text": item.get("setup_text") or "",
            "new_text": item.get("new_setup_text") or "",
            "file_changes": {},
            "profile": None,
        },
        "diagnosis": item.get("diagnosis")
        or {"summary": "", "issues": [], "conflicts": [], "missing": []},
        "changes": item.get("changes") or [],
        "test_plan": test_plan,
        "explanation": item.get("explanation") or "",
        "warnings": item.get("warnings") or [],
        "llm_used": False,
        "llm_error": None,
        "saved_path": item.get("saved_path"),
        "status": item.get("status"),
        "result": item.get("result"),
        "session_id": item.get("session_id"),
    }


@router.get("/ac/live")
def ac_live() -> dict:
    snapshot = read_live()
    return snapshot.to_dict()


@router.post("/sessions")
def create_session_endpoint(req: SessionCreate) -> dict:
    from app import catalog

    car_name = req.car_id
    track_name = req.track_id
    cat = catalog.load_catalog()
    for car in cat.get("cars", []):
        if car["car_id"] == req.car_id:
            car_name = car["name"]
            break
    for track in cat.get("tracks", []):
        if track["track_id"] == req.track_id:
            track_name = track["name"]
            break
    session_id = store.create_session(
        {
            "name": req.name,
            "car_id": req.car_id,
            "car_name": car_name,
            "track_id": req.track_id,
            "track_name": track_name,
            "base_setup_path": req.base_setup_path,
            "notes": req.notes,
        }
    )
    session = store.get_session(session_id)
    return session or {"id": session_id}


@router.get("/sessions")
def list_sessions_endpoint(limit: int = 50) -> dict:
    return {"sessions": store.list_sessions(limit=min(max(limit, 1), 200))}


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: int) -> dict:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return session


@router.patch("/sessions/{session_id}")
def update_session_endpoint(session_id: int, req: SessionUpdate) -> dict:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    store.update_session(session_id, req.model_dump(exclude_none=True))
    return store.get_session(session_id) or {"id": session_id}


@router.get("/llm/status")
def llm_status() -> dict:
    return llm.status()


@router.post("/llm/narrate")
def llm_narrate(req: LlmNarrateRequest) -> dict:
    analysis = store.get_analysis(req.analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")
    payload = {
        "car": analysis.get("car_name"),
        "track": analysis.get("track_name"),
        "condition": (analysis.get("context") or {}).get("condition"),
        "issues": (analysis.get("diagnosis") or {}).get("issues"),
        "changes": analysis.get("changes"),
        "test_plan": analysis.get("test_plan"),
        "warnings": analysis.get("warnings"),
        "driver_notes": (analysis.get("feedback") or {}).get("notes"),
    }
    text = llm.narrate(payload)
    if not text:
        raise HTTPException(status_code=503, detail="Ollama no está disponible o no tiene un modelo cargado.")
    store.set_explanation(req.analysis_id, text)
    return {"explanation": text}
