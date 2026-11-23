from __future__ import annotations

import ctypes
import mmap
from dataclasses import dataclass
from typing import Any

AC_STATUS = ctypes.c_int32
AC_OFF = 0
AC_REPLAY = 1
AC_LIVE = 2
AC_PAUSE = 3
AC_SESSION_TYPE = ctypes.c_int32
AC_UNKNOWN = -1
AC_PRACTICE = 0
AC_QUALIFY = 1
AC_RACE = 2
AC_HOTLAP = 3
AC_TIME_ATTACK = 4
AC_DRIFT = 5
AC_DRAG = 6

from ctypes import c_char, c_float, c_int32, c_wchar


class vec3(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("x", c_float), ("y", c_float), ("z", c_float)]


class SPageFilePhysics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32),
        ("gas", c_float),
        ("brake", c_float),
        ("fuel", c_float),
        ("gear", c_int32),
        ("rpms", c_int32),
        ("steerAngle", c_float),
        ("speedKmh", c_float),
        ("velocity", c_float * 3),
        ("accG", c_float * 3),
        ("wheelSlip", c_float * 4),
        ("wheelLoad", c_float * 4),
        ("wheelsPressure", c_float * 4),
        ("wheelAngularSpeed", c_float * 4),
        ("tyreWear", c_float * 4),
        ("tyreDirtyLevel", c_float * 4),
        ("tyreCoreTemperature", c_float * 4),
        ("camberRAD", c_float * 4),
        ("suspensionTravel", c_float * 4),
        ("drs", c_float),
        ("tc", c_float),
        ("heading", c_float),
        ("pitch", c_float),
        ("roll", c_float),
        ("cgHeight", c_float),
        ("carDamage", c_float * 5),
        ("numberOfTyresOut", c_int32),
        ("pitLimiterOn", c_int32),
        ("abs", c_float),
        ("kersCharge", c_float),
        ("kersInput", c_float),
        ("autoShifterOn", c_int32),
        ("rideHeight", c_float * 2),
        ("turboBoost", c_float),
        ("ballast", c_float),
        ("airDensity", c_float),
        ("airTemp", c_float),
        ("roadTemp", c_float),
        ("localAngularVel", c_float * 3),
        ("finalFF", c_float),
        ("performanceMeter", c_float),
        ("engineBrake", c_int32),
        ("ersRecoveryLevel", c_int32),
        ("ersPowerLevel", c_int32),
        ("ersHeatCharging", c_int32),
        ("ersIsCharging", c_int32),
        ("kersCurrentKJ", c_float),
        ("drsAvailable", c_int32),
        ("drsEnabled", c_int32),
        ("brakeTemp", c_float * 4),
        ("clutch", c_float),
        ("tyreTempI", c_float * 4),
        ("tyreTempM", c_float * 4),
        ("tyreTempO", c_float * 4),
        ("isAIControlled", c_int32),
        ("tyreContactPoint", c_float * 4 * 3),
        ("tyreContactNormal", c_float * 4 * 3),
        ("tyreContactHeading", c_float * 4 * 3),
        ("brakeBias", c_float),
        ("localVelocity", c_float * 3),
    ]


class SPageFileGraphic(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32),
        ("status", AC_STATUS),
        ("session", AC_SESSION_TYPE),
        ("currentTime", c_wchar * 15),
        ("lastTime", c_wchar * 15),
        ("bestTime", c_wchar * 15),
        ("split", c_wchar * 15),
        ("completedLaps", c_int32),
        ("position", c_int32),
        ("iCurrentTime", c_int32),
        ("iLastTime", c_int32),
        ("iBestTime", c_int32),
        ("sessionTimeLeft", c_float),
        ("distanceTraveled", c_float),
        ("isInPit", c_int32),
        ("currentSectorIndex", c_int32),
        ("lastSectorTime", c_int32),
        ("numberOfLaps", c_int32),
        ("tyreCompound", c_wchar * 33),
        ("replayTimeMultiplier", c_float),
        ("normalizedCarPosition", c_float),
        ("carCoordinates", c_float * 3),
        ("penaltyTime", c_float),
        ("flag", ctypes.c_int32),
        ("idealLineOn", c_int32),
        ("isInPitLine", c_int32),
        ("surfaceGrip", c_float),
        ("mandatoryPitDone", c_int32),
        ("windSpeed", c_float),
        ("windDirection", c_float),
    ]


class SPageFileStatic(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("_smVersion", c_wchar * 15),
        ("_acVersion", c_wchar * 15),
        ("numberOfSessions", c_int32),
        ("numCars", c_int32),
        ("carModel", c_wchar * 33),
        ("track", c_wchar * 33),
        ("playerName", c_wchar * 33),
        ("playerSurname", c_wchar * 33),
        ("playerNick", c_wchar * 33),
        ("sectorCount", c_int32),
        ("maxTorque", c_float),
        ("maxPower", c_float),
        ("maxRpm", c_int32),
        ("maxFuel", c_float),
        ("suspensionMaxTravel", c_float * 4),
        ("tyreRadius", c_float * 4),
        ("maxTurboBoost", c_float),
        ("airTemp", c_float),
        ("roadTemp", c_float),
        ("penaltiesEnabled", c_int32),
        ("aidFuelRate", c_float),
        ("aidTireRate", c_float),
        ("aidMechanicalDamage", c_float),
        ("aidAllowTyreBlankets", c_int32),
        ("aidStability", c_float),
        ("aidAutoClutch", c_int32),
        ("aidAutoBlip", c_int32),
        ("hasDRS", c_int32),
        ("hasERS", c_int32),
        ("hasKERS", c_int32),
        ("kersMaxJ", c_float),
        ("engineBrakeSettingsCount", c_int32),
        ("ersPowerControllerCount", c_int32),
        ("trackSPlineLength", c_float),
        ("trackConfiguration", c_wchar * 33),
        ("ersMaxJ", c_float),
        ("isTimedRace", c_int32),
        ("hasExtraLap", c_int32),
        ("carSkin", c_wchar * 33),
        ("reversedGridPositions", c_int32),
        ("pitWindowStart", c_int32),
        ("pitWindowEnd", c_int32),
    ]


@dataclass
class LiveSnapshot:
    available: bool
    status: str
    car_id: str | None = None
    track_id: str | None = None
    track_config: str | None = None
    player: str | None = None
    session_type: str | None = None
    air_temp_c: float | None = None
    road_temp_c: float | None = None
    surface_grip: float | None = None
    fuel_l: float | None = None
    tyre_compound: str | None = None
    completed_laps: int | None = None
    best_lap_ms: int | None = None
    last_lap_ms: int | None = None
    current_lap_ms: int | None = None
    tyre_temps: dict[str, dict[str, float | None]] | None = None
    tyre_pressures: dict[str, float] | None = None
    tyre_wear: dict[str, float] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


TYRE_KEYS = ("lf", "rf", "lr", "rr")


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip("\x00 ").strip()
    return text or None


def read_live() -> LiveSnapshot:
    try:
        physics_mm = mmap.mmap(0, ctypes.sizeof(SPageFilePhysics), "acpmf_physics")
        graphics_mm = mmap.mmap(0, ctypes.sizeof(SPageFileGraphic), "acpmf_graphics")
        static_mm = mmap.mmap(0, ctypes.sizeof(SPageFileStatic), "acpmf_static")
    except (OSError, FileNotFoundError, ValueError) as exc:
        return LiveSnapshot(available=False, status="not_running", error=str(exc))

    try:
        physics = SPageFilePhysics.from_buffer(physics_mm)
        graphics = SPageFileGraphic.from_buffer(graphics_mm)
        static = SPageFileStatic.from_buffer(static_mm)

        status_code = int(graphics.status)
        status_name = {AC_OFF: "off", AC_REPLAY: "replay", AC_LIVE: "live", AC_PAUSE: "paused"}.get(
            status_code, "unknown"
        )

        session_code = int(graphics.session)
        session_name = {
            AC_PRACTICE: "practice",
            AC_QUALIFY: "qualifying",
            AC_RACE: "race",
            AC_HOTLAP: "test",
            AC_TIME_ATTACK: "test",
        }.get(session_code, "practice")

        car_id = _clean_text(static.carModel)
        track_id = _clean_text(static.track)
        track_config = _clean_text(static.trackConfiguration)

        tyre_temps = {}
        tyre_pressures = {}
        tyre_wear = {}
        for index, key in enumerate(TYRE_KEYS):
            try:
                tyre_temps[key] = {
                    "inner": float(physics.tyreTempI[index]),
                    "middle": float(physics.tyreTempM[index]),
                    "outer": float(physics.tyreTempO[index]),
                }
                tyre_pressures[key] = float(physics.wheelsPressure[index])
                tyre_wear[key] = float(physics.tyreWear[index])
            except (IndexError, ValueError):
                pass

        best = int(graphics.iBestTime) if graphics.iBestTime and graphics.iBestTime > 0 else None
        last = int(graphics.iLastTime) if graphics.iLastTime and graphics.iLastTime > 0 else None
        current = int(graphics.iCurrentTime) if graphics.iCurrentTime and graphics.iCurrentTime > 0 else None

        compound = _clean_text(graphics.tyreCompound)
        player = " ".join(
            part for part in (_clean_text(static.playerName), _clean_text(static.playerSurname)) if part
        )

        snapshot = LiveSnapshot(
            available=status_name in ("live", "paused", "replay"),
            status=status_name,
            car_id=car_id,
            track_id=track_id,
            track_config=track_config,
            player=player or None,
            session_type=session_name,
            air_temp_c=float(physics.airTemp),
            road_temp_c=float(physics.roadTemp),
            surface_grip=float(graphics.surfaceGrip) if graphics.surfaceGrip else None,
            fuel_l=float(physics.fuel),
            tyre_compound=compound,
            completed_laps=int(graphics.completedLaps),
            best_lap_ms=best,
            last_lap_ms=last,
            current_lap_ms=current,
            tyre_temps=tyre_temps,
            tyre_pressures=tyre_pressures,
            tyre_wear=tyre_wear,
        )
        return snapshot
    finally:
        try:
            physics_mm.close()
        except Exception:
            pass
        try:
            graphics_mm.close()
        except Exception:
            pass
        try:
            static_mm.close()
        except Exception:
            pass
