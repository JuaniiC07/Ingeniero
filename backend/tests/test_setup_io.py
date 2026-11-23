from __future__ import annotations

from pathlib import Path

from app.setup_io import SetupFile

SPA = Path(r"C:\Users\juanm\Documentos\Assetto Corsa\setups\fsr_audi_lms_evo_ii_gt3\spa\14 3.ini")
BATHURST = Path(r"C:\Users\juanm\Documentos\Assetto Corsa\setups\fsr_audi_lms_evo_ii_gt3\rt_bathurst\59 8.ini")


def test_roundtrip_bytes() -> None:
    for path in (SPA, BATHURST):
        raw = path.read_bytes()
        setup = SetupFile.parse(raw.decode("utf-8-sig", errors="replace"))
        assert setup.text == raw.decode("utf-8-sig", errors="replace")
        assert setup.with_values({}) == setup.text


def test_values_parsed() -> None:
    setup = SetupFile.from_path(SPA)
    assert setup.get("CAR") is None  # CAR has MODEL, not VALUE
    assert setup.get_float("PRESSURE_LF") == 19
    assert setup.get_float("ARB_FRONT") == 40000
    assert setup.get_float("CAMBER_LF") == -40
    assert setup.get("__EXT_PATCH") is None


def test_single_change_preserves_everything_else() -> None:
    setup = SetupFile.from_path(SPA)
    changed = setup.with_values({"PRESSURE_LF": "20", "ARB_REAR": "15000"})
    reparsed = SetupFile.parse(changed)
    assert reparsed.get_float("PRESSURE_LF") == 20
    assert reparsed.get_float("ARB_REAR") == 15000
    # only the two VALUE tokens differ
    diff = setup.changed_sections(reparsed)
    assert diff == {"PRESSURE_LF": ("19", "20"), "ARB_REAR": ("10000", "15000")}
    assert reparsed.text.count("\n") == setup.text.count("\n")
