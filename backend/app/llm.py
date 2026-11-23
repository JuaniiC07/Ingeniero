from __future__ import annotations

import json
import os
from typing import Any

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "").strip()

PREFERRED = ("qwen3", "qwen2.5", "llama3.1", "llama3", "mistral", "gemma3", "phi4", "deepseek")


def status() -> dict[str, Any]:
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        response.raise_for_status()
        models = [item.get("name", "") for item in response.json().get("models", [])]
        usable = [name for name in models if name]
        model = OLLAMA_MODEL or _pick_model(usable)
        return {
            "available": True,
            "base_url": OLLAMA_URL,
            "models": usable,
            "model": model,
            "ready": bool(model),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "base_url": OLLAMA_URL,
            "models": [],
            "model": OLLAMA_MODEL or None,
            "ready": False,
            "error": str(exc),
        }


def _pick_model(models: list[str]) -> str | None:
    if not models:
        return None
    for prefix in PREFERRED:
        for name in models:
            if name.lower().startswith(prefix):
                return name
    return models[0]


def narrate(payload: dict[str, Any]) -> str | None:
    info = status()
    if not info.get("ready"):
        return None
    model = info["model"]
    system = (
        "Eres un ingeniero de pista de simracing que habla en español rioplatense, directo y práctico. "
        "Explicás el diagnóstico y el plan de setup a un piloto. Reglas estrictas:\n"
        "1) No inventes valores de setup ni cambios nuevos: usá únicamente los que aparecen en el JSON.\n"
        "2) No inventes datos de telemetría ni temperaturas que no estén en el JSON.\n"
        "3) Sé claro y útil: entre 120 y 260 palabras.\n"
        "4) Mencioná el riesgo de cada cambio y cómo validarlo en pista.\n"
        "5) Si el piloto dejó notas, referite a ellas concretamente (curvas, fases).\n"
        "6) Si faltan datos (temperaturas, presiones, tiempos), decilo y sugerí qué cargar.\n"
        "7) Estructura: un párrafo de diagnóstico, una lista corta de cambios con su razón, "
        "y un párrafo final de cómo probarlo.\n"
        "Respondé en texto plano, sin markdown complejo (solo guiones para listas)."
    )
    user = (
        "Este es el análisis del ingeniero. Escribí la explicación para el piloto usando solo estos datos:\n"
        + _compact(payload)
    )
    body = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0.5, "num_predict": 700},
    }
    try:
        response = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=120)
        response.raise_for_status()
        data = response.json()
        content = (data.get("message") or {}).get("content") or data.get("response")
        return content.strip() if content else None
    except Exception:
        return None


def _compact(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)[:14000]
