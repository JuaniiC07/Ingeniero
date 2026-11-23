from __future__ import annotations

from pathlib import Path

import pytest

from app import config
from app.car_profiles import build_profile
from app.engine import analyze
from app.schemas import ContextIn, FeedbackIn, SymptomIn
from app.setup_io import SetupFile

AUDI = "fsr_audi_lms_evo_ii_gt3"
SPA = config.setups_dir() / AUDI / "spa" / "14 3.ini"


def _require(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"Setup de referencia no disponible: {path}")
    if not (config.cars_dir() / AUDI).exists():
        pytest.skip("Assetto Corsa no está instalado en esta máquina.")


def test_audi_profile_uses_game_units() -> None:
    _require(SPA)
    profile = build_profile(AUDI, SetupFile.from_path(SPA))
    params = profile.by_section()

    camber = params["CAMBER_LF"]
    assert camber.mode == "scaled"
    assert camber.display() == pytest.approx(-4.0)
    assert camber.step_display() == pytest.approx(0.1)

    # TOE uses SHOW_CLICKS=2: the game shows value / STEP.
    toe = params["TOE_OUT_LF"]
    assert toe.mode == "clicks2"
    assert toe.display() == pytest.approx(2.0)
    assert toe.unit == "click"

    arb = params["ARB_FRONT"]
    assert arb.mode == "physical"
    assert arb.step == pytest.approx(10000)
    assert arb.unit == "N/m"


def test_audi_changes_stay_inside_envelope() -> None:
    _require(SPA)
    setup = SetupFile.from_path(SPA)
    profile = build_profile(AUDI, setup)
    params = profile.by_section()

    feedback = FeedbackIn(
        symptoms=[
            SymptomIn(type="understeer", phase="mid", speed="fast", severity=2),
            SymptomIn(type="wheelspin", phase="exit", speed="slow", severity=2),
        ]
    )
    result = analyze(
        setup=setup,
        car_id=AUDI,
        track_id="spa",
        setup_name="14 3",
        setup_path=str(SPA),
        track_name="Spa",
        track_type="fast",
        context=ContextIn(condition="dry", laps_target=4),
        feedback=feedback,
    )

    assert result["changes"], "debería proponer al menos un cambio"
    for section, new_value in result["setup"]["file_changes"].items():
        param = params[section]
        value = float(new_value)
        assert param.minimum <= value <= param.maximum
        delta = abs(value - param.current)
        assert delta >= param.step * 0.5

    # The original file must keep its structure: only VALUE tokens change.
    assert setup.text.count("\n") == result["setup"]["new_text"].count("\n")


def test_unknown_symptoms_do_not_invent_values() -> None:
    _require(SPA)
    setup = SetupFile.from_path(SPA)
    result = analyze(
        setup=setup,
        car_id=AUDI,
        track_id="spa",
        setup_name="14 3",
        setup_path=str(SPA),
        track_name="Spa",
        track_type="balanced",
        context=ContextIn(),
        feedback=FeedbackIn(),
    )
    assert result["changes"] == []
    assert result["setup"]["new_text"] == setup.text
