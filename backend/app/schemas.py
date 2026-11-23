from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SymptomType = Literal[
    "understeer",
    "oversteer",
    "wheelspin",
    "lockup_front",
    "lockup_rear",
    "braking_instability",
    "bottoming",
    "kerb",
    "tyre_inner_hot_front",
    "tyre_inner_hot_rear",
    "tyre_outer_hot_front",
    "tyre_outer_hot_rear",
    "tyre_center_hot",
    "top_speed",
    "low_grip",
]

Phase = Literal["entry", "mid", "exit", "braking", "straight", "any"]
Speed = Literal["slow", "medium", "fast", "any"]


class SymptomIn(BaseModel):
    type: SymptomType
    phase: Phase = "any"
    speed: Speed = "any"
    severity: int = Field(default=1, ge=0, le=3)


class TyreTempIn(BaseModel):
    inner: float | None = None
    middle: float | None = None
    outer: float | None = None


class ContextIn(BaseModel):
    condition: Literal["dry", "damp", "wet"] = "dry"
    track_type: str | None = None
    air_temp_c: float | None = None
    track_temp_c: float | None = None
    grip: float | None = Field(default=None, ge=0, le=100)
    session_type: Literal["practice", "qualifying", "race", "test"] = "practice"
    laps_target: int = Field(default=5, ge=1, le=60)
    fuel_l: float | None = None
    compound: str | None = None


class FeedbackIn(BaseModel):
    symptoms: list[SymptomIn] = Field(default_factory=list)
    notes: str = ""
    best_lap_ms: int | None = None
    avg_lap_ms: int | None = None
    laps_completed: int | None = None
    tyre_temps: dict[str, TyreTempIn] | None = None
    hot_pressures: dict[str, float] | None = None


class AnalyzeRequest(BaseModel):
    setup_path: str | None = None
    setup_text: str | None = None
    setup_name: str | None = None
    car_id: str | None = None
    track_id: str | None = None
    session_id: int | None = None
    context: ContextIn = Field(default_factory=ContextIn)
    feedback: FeedbackIn = Field(default_factory=FeedbackIn)
    use_llm: bool = False


class SaveRequest(BaseModel):
    analysis_id: int
    name: str | None = None
    overwrite: bool = False


class ResultRequest(BaseModel):
    analysis_id: int
    best_lap_ms: int | None = None
    avg_lap_ms: int | None = None
    notes: str = ""
    outcome: Literal["better", "same", "worse", "unknown"] = "unknown"


class TextRequest(BaseModel):
    text: str

class SessionCreate(BaseModel):
    car_id: str
    track_id: str | None = None
    name: str | None = None
    base_setup_path: str | None = None
    notes: str = ""

class SessionUpdate(BaseModel):
    name: str | None = None
    current_setup_path: str | None = None
    base_setup_path: str | None = None
    status: str | None = None
    notes: str | None = None


class InspectRequest(BaseModel):
    text: str
    car_id: str | None = None
    track_id: str | None = None
    name: str | None = None


class LlmNarrateRequest(BaseModel):
    analysis_id: int
