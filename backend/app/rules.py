from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.car_profiles import CarProfile

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


@dataclass
class ChangeSpec:
    role: str
    direction: int
    steps: float
    weight: float
    category: str
    risk: str
    reason: str
    effect: str


@dataclass
class Rule:
    id: str
    name: str
    symptoms: list[str]
    phases: list[str]
    speeds: list[str]
    weight: float
    changes: list[ChangeSpec] = field(default_factory=list)


@dataclass
class KnowledgeBase:
    rules: list[Rule]
    max_changes: int = 3
    max_changes_wet: int = 2
    min_score: float = 0.35


_CACHE: KnowledgeBase | None = None


def load_knowledge() -> KnowledgeBase:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    rules: list[Rule] = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        for item in raw.get("rules", []):
            changes = [
                ChangeSpec(
                    role=change["role"],
                    direction=int(change["direction"]),
                    steps=float(change.get("steps", 1)),
                    weight=float(change.get("weight", 1.0)),
                    category=change.get("category", "mechanical"),
                    risk=change.get("risk", "medium"),
                    reason=change.get("reason", ""),
                    effect=change.get("effect", ""),
                )
                for change in item.get("changes", [])
            ]
            rules.append(
                Rule(
                    id=item["id"],
                    name=item.get("name", item["id"]),
                    symptoms=list(item.get("symptoms", [])),
                    phases=list(item.get("phases", ["any"])),
                    speeds=list(item.get("speeds", ["any"])),
                    weight=float(item.get("weight", 1.0)),
                    changes=changes,
                )
            )
    defaults = (yaml.safe_load((KNOWLEDGE_DIR / "gt3_formula.yaml").read_text(encoding="utf-8")) or {}).get(
        "defaults", {}
    )
    _CACHE = KnowledgeBase(
        rules=rules,
        max_changes=int(defaults.get("max_changes", 3)),
        max_changes_wet=int(defaults.get("max_changes_wet", 2)),
        min_score=float(defaults.get("min_score", 0.35)),
    )
    return _CACHE


def _by_sections(profile: CarProfile, sections: list[str]) -> list[str]:
    wanted = [section.upper() for section in sections]
    available = {param.section for param in profile.params if param.has_value}
    return [section for section in wanted if section in available]


def _wing_candidates(profile: CarProfile, want_front: bool) -> list[str]:
    wings = [p for p in profile.params if p.section.startswith("WING_") and p.has_value]
    if not wings:
        return []
    front_tokens = ("front", "splitter", "delantera", "delantero")
    rear_tokens = ("rear", "spoiler", "trasera", "trasero", "ala")
    tokens = front_tokens if want_front else rear_tokens
    matches = [p for p in wings if any(token in p.label.lower() for token in tokens)]
    if matches:
        return [matches[0].section]
    if want_front:
        # Only use a front-wing role when the car actually has a second wing
        # or an explicit front/splitter label; otherwise it is a rear wing only.
        if len(wings) >= 2:
            return [wings[0].section]
        return []
    # A single WING_* parameter is normally the rear wing/spoiler.
    if len(wings) == 1:
        return [wings[0].section]
    return [wings[-1].section]


def resolve_role(profile: CarProfile, role: str) -> list[str]:
    role = role.lower()
    fixed: dict[str, list[str]] = {
        "front_arb": ["ARB_FRONT"],
        "rear_arb": ["ARB_REAR"],
        "front_toe": ["TOE_OUT_LF", "TOE_OUT_RF"],
        "rear_toe": ["TOE_OUT_LR", "TOE_OUT_RR"],
        "front_camber": ["CAMBER_LF", "CAMBER_RF"],
        "rear_camber": ["CAMBER_LR", "CAMBER_RR"],
        "front_spring": ["SPRING_RATE_LF", "SPRING_RATE_RF"],
        "rear_spring": ["SPRING_RATE_LR", "SPRING_RATE_RR"],
        "front_bump": ["DAMP_BUMP_LF", "DAMP_BUMP_RF"],
        "rear_bump": ["DAMP_BUMP_LR", "DAMP_BUMP_RR"],
        "front_rebound": ["DAMP_REBOUND_LF", "DAMP_REBOUND_RF"],
        "rear_rebound": ["DAMP_REBOUND_LR", "DAMP_REBOUND_RR"],
        "front_fast_bump": ["DAMP_FAST_BUMP_LF", "DAMP_FAST_BUMP_RF"],
        "rear_fast_bump": ["DAMP_FAST_BUMP_LR", "DAMP_FAST_BUMP_RR"],
        "front_fast_rebound": ["DAMP_FAST_REBOUND_LF", "DAMP_FAST_REBOUND_RF"],
        "rear_fast_rebound": ["DAMP_FAST_REBOUND_LR", "DAMP_FAST_REBOUND_RR"],
        "front_ride": ["ROD_LENGTH_LF", "ROD_LENGTH_RF"],
        "rear_ride": ["ROD_LENGTH_LR", "ROD_LENGTH_RR"],
        "front_packer": ["PACKER_RANGE_LF", "PACKER_RANGE_RF"],
        "rear_packer": ["PACKER_RANGE_LR", "PACKER_RANGE_RR"],
        "front_bumpstop": ["BUMPSTOP_LF", "BUMPSTOP_RF"],
        "rear_bumpstop": ["BUMPSTOP_LR", "BUMPSTOP_RR"],
        "front_pressure": ["PRESSURE_LF", "PRESSURE_RF"],
        "rear_pressure": ["PRESSURE_LR", "PRESSURE_RR"],
        "brake_bias": ["FRONT_BIAS"],
        "diff_power": ["DIFF_POWER"],
        "diff_coast": ["DIFF_COAST"],
        "diff_preload": ["DIFF_PRELOAD"],
        "tc": ["TRACTION_CONTROL"],
        "abs": ["ABS"],
        "fuel": ["FUEL"],
    }
    if role in fixed:
        return _by_sections(profile, fixed[role])
    if role == "rear_wing":
        return _wing_candidates(profile, want_front=False)
    if role == "front_wing":
        return _wing_candidates(profile, want_front=True)
    # Allow rules to reference an exact AC section name.
    if role.upper() in {p.section for p in profile.params}:
        return _by_sections(profile, [role])
    return []
