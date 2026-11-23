from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.car_profiles import CarProfile, ParamProfile, build_profile
from app.rules import KnowledgeBase, load_knowledge, resolve_role
from app.schemas import ContextIn, FeedbackIn, SymptomIn
from app.setup_io import SetupFile, format_number

SYMPTOM_LABELS = {
    "understeer": "Subviraje",
    "oversteer": "Sobreviraje",
    "wheelspin": "Falta de tracción",
    "lockup_front": "Bloqueo delantero",
    "lockup_rear": "Bloqueo trasero",
    "braking_instability": "Inestabilidad en frenada",
    "bottoming": "Tope de suspensión",
    "kerb": "Problema sobre pianos",
    "tyre_inner_hot_front": "Goma delantera caliente por dentro",
    "tyre_inner_hot_rear": "Goma trasera caliente por dentro",
    "tyre_outer_hot_front": "Goma delantera caliente por fuera",
    "tyre_outer_hot_rear": "Goma trasera caliente por fuera",
    "tyre_center_hot": "Goma caliente en el centro",
    "top_speed": "Falta de velocidad punta",
    "low_grip": "Poco agarre general",
}

PHASE_LABELS = {
    "entry": "entrada",
    "mid": "medio",
    "exit": "salida",
    "braking": "frenada",
    "straight": "recta",
    "any": "general",
}

SPEED_LABELS = {
    "slow": "lenta",
    "medium": "media",
    "fast": "rápida",
    "any": "todo tipo",
}

SPEED_PLURAL = {"slow": "lentas", "medium": "medias", "fast": "rápidas"}

RISK_LABELS = {"low": "bajo", "medium": "medio", "high": "alto"}

CATEGORY_LABELS = {
    "mechanical": "Mecánica",
    "alignment": "Alineación",
    "aero": "Aerodinámica",
    "diff": "Diferencial",
    "brakes": "Frenos",
    "tyres": "Neumáticos",
    "electronics": "Electrónica",
    "dampers": "Amortiguadores",
    "ride_height": "Altura",
}


@dataclass
class Candidate:
    sections: list[str]
    role: str
    direction: int
    steps: float
    rule_id: str
    rule_name: str
    reason: str
    effect: str
    risk: str
    category: str
    score: float


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _issue_label(symptom: SymptomIn) -> str:
    base = SYMPTOM_LABELS.get(symptom.type, symptom.type)
    phase = PHASE_LABELS.get(symptom.phase, symptom.phase)
    bits = []
    if phase != "general":
        bits.append(phase)
    if symptom.speed in SPEED_PLURAL:
        bits.append(f"curvas {SPEED_PLURAL[symptom.speed]}")
    return f"{base} ({', '.join(bits)})" if bits else base


def _dedupe_symptoms(symptoms: list[SymptomIn]) -> list[SymptomIn]:
    best: dict[tuple[str, str, str], SymptomIn] = {}
    for symptom in symptoms:
        if symptom.severity <= 0:
            continue
        key = (symptom.type, symptom.phase, symptom.speed)
        previous = best.get(key)
        if previous is None or symptom.severity > previous.severity:
            best[key] = symptom
    return list(best.values())


def _tyre_symptoms(feedback: FeedbackIn) -> tuple[list[SymptomIn], list[str]]:
    symptoms: list[SymptomIn] = []
    notes: list[str] = []
    temps = feedback.tyre_temps or {}
    if not temps:
        return symptoms, notes

    def avg(values: list[float | None]) -> float | None:
        present = [value for value in values if value is not None]
        return sum(present) / len(present) if present else None

    for axle, keys in (("front", ("lf", "rf")), ("rear", ("lr", "rr"))):
        inner = avg([temps[k].inner if k in temps and temps[k] else None for k in keys])
        outer = avg([temps[k].outer if k in temps and temps[k] else None for k in keys])
        middle = avg([temps[k].middle if k in temps and temps[k] else None for k in keys])
        if inner is None or outer is None:
            continue
        if inner - outer >= 12:
            severity = min(3, max(1, round((inner - outer) / 10)))
            symptoms.append(SymptomIn(type=f"tyre_inner_hot_{axle}", severity=severity))
            notes.append(f"Temperaturas {axle}s: interior {inner:.0f}°C vs exterior {outer:.0f}°C.")
        elif outer - inner >= 12:
            severity = min(3, max(1, round((outer - inner) / 10)))
            symptoms.append(SymptomIn(type=f"tyre_outer_hot_{axle}", severity=severity))
            notes.append(f"Temperaturas {axle}s: exterior {outer:.0f}°C vs interior {inner:.0f}°C.")
        if middle is not None and middle - max(inner, outer) >= 8:
            symptoms.append(SymptomIn(type="tyre_center_hot", severity=2))
            notes.append(f"Temperaturas {axle}s: centro {middle:.0f}°C, más caliente que los bordes.")
    return symptoms, notes


def _context_factor(category: str, risk: str, context: ContextIn, track_type: str) -> float:
    factor = 1.0
    if context.condition in ("damp", "wet"):
        if category in ("mechanical", "diff", "brakes"):
            factor *= 0.85
        if category == "aero":
            factor *= 1.1
        if category == "ride_height":
            factor *= 1.15
        if risk == "high":
            factor *= 0.8
        if category == "electronics":
            factor *= 1.1
    if track_type == "bumpy":
        if category in ("dampers", "ride_height"):
            factor *= 1.2
        if category == "mechanical":
            factor *= 0.92
    elif track_type == "fast":
        if category == "aero":
            factor *= 1.15
        if category in ("mechanical", "diff"):
            factor *= 0.95
    elif track_type == "street":
        if category in ("aero", "brakes"):
            factor *= 1.1
        if risk == "high":
            factor *= 0.9
    elif track_type == "oval":
        if category == "aero":
            factor *= 1.1
        if category in ("alignment", "diff"):
            factor *= 0.9
    return factor


def _candidates(
    profile: CarProfile,
    symptoms: list[SymptomIn],
    context: ContextIn,
    track_type: str,
    kb: KnowledgeBase,
) -> list[Candidate]:
    out: list[Candidate] = []
    for symptom in symptoms:
        for rule in kb.rules:
            if symptom.type not in rule.symptoms:
                continue
            if "any" not in rule.phases and symptom.phase not in rule.phases:
                if symptom.phase != "any":
                    continue
                phase_factor = 0.65
            else:
                phase_factor = 1.0 if symptom.phase in rule.phases else 0.8
            if "any" not in rule.speeds and symptom.speed not in rule.speeds:
                if symptom.speed != "any":
                    continue
                speed_factor = 0.7
            else:
                speed_factor = 1.0 if symptom.speed in rule.speeds else 0.85
            severity_factor = 0.6 + 0.2 * symptom.severity
            for change in rule.changes:
                sections = resolve_role(profile, change.role)
                if not sections:
                    continue
                factor = _context_factor(change.category, change.risk, context, track_type)
                score = (
                    rule.weight
                    * change.weight
                    * severity_factor
                    * phase_factor
                    * speed_factor
                    * factor
                )
                out.append(
                    Candidate(
                        sections=sections,
                        role=change.role,
                        direction=change.direction,
                        steps=change.steps,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        reason=change.reason,
                        effect=change.effect,
                        risk=change.risk,
                        category=change.category,
                        score=score,
                    )
                )
    return out


def _merge_candidates(
    candidates: list[Candidate], profile: CarProfile
) -> tuple[list[Candidate], list[str]]:
    labels = {param.section: param.label for param in profile.params}
    merged: dict[tuple[tuple[str, ...], int], Candidate] = {}
    for candidate in candidates:
        key = (tuple(candidate.sections), candidate.direction)
        previous = merged.get(key)
        if previous is None:
            merged[key] = candidate
        else:
            previous.score = min(previous.score + candidate.score * 0.5, 2.5)
            if candidate.score > previous.score:
                previous.reason = candidate.reason
                previous.effect = candidate.effect
            previous.rule_id = f"{previous.rule_id}+{candidate.rule_id}"

    conflicts: list[str] = []
    by_section: dict[str, list[Candidate]] = {}
    for candidate in merged.values():
        for section in candidate.sections:
            by_section.setdefault(section, []).append(candidate)

    dropped: set[tuple[tuple[str, ...], int]] = set()
    for section, items in by_section.items():
        positives = [c for c in items if c.direction > 0]
        negatives = [c for c in items if c.direction < 0]
        if not positives or not negatives:
            continue
        best_positive = max(positives, key=lambda c: c.score)
        best_negative = max(negatives, key=lambda c: c.score)
        winner = best_positive if best_positive.score >= best_negative.score else best_negative
        loser = best_negative if winner is best_positive else best_positive
        if loser.score / max(winner.score, 1e-6) > 0.7:
            dropped.add((tuple(loser.sections), loser.direction))
            dropped.add((tuple(winner.sections), winner.direction))
            conflicts.append(
                f"Hay señales opuestas sobre {labels.get(section, section)}: se descartaron ambos cambios y conviene hacer una prueba A/B."
            )
        else:
            dropped.add((tuple(loser.sections), loser.direction))
    result = [c for key, c in merged.items() if key not in dropped]
    return result, conflicts


def _select(
    candidates: list[Candidate], kb: KnowledgeBase, max_changes: int
) -> list[Candidate]:
    selected: list[Candidate] = []
    used_sections: set[str] = set()
    category_counts: Counter[str] = Counter()
    remaining = list(candidates)

    while remaining and len(selected) < max_changes:
        best: Candidate | None = None
        best_score = -1.0
        for candidate in remaining:
            if any(section in used_sections for section in candidate.sections):
                continue
            adjusted = candidate.score * (0.72 ** category_counts[candidate.category])
            if adjusted > best_score:
                best = candidate
                best_score = adjusted
        if best is None:
            break
        if selected and best_score < kb.min_score:
            break
        selected.append(best)
        used_sections.update(best.sections)
        category_counts[best.category] += 1
        remaining.remove(best)
    return selected


def _snap(param: ParamProfile, current: float, value: float) -> float:
    """Keep the change on the step grid measured from the driver's own value.

    Mods often store values that do not align with the declared grid, so
    anchoring to MIN would silently move the base setup. We always move whole
    steps from the current value and only clamp to the accepted envelope.
    """
    if param.step <= 0:
        return _clamp(value, param.minimum, param.maximum)
    steps = round((value - current) / param.step)
    if steps == 0:
        steps = 1 if value >= current else -1
    snapped = current + steps * param.step
    return _clamp(snapped, param.minimum, param.maximum)


def _apply_candidates(
    profile: CarProfile,
    setup: SetupFile,
    candidates: list[Candidate],
) -> tuple[list[dict], dict[str, str], str, list[str]]:
    by_section = profile.by_section()
    working = setup.numeric()
    changes: list[dict] = []
    file_changes: dict[str, str] = {}
    limit_notes: list[str] = []

    for candidate in candidates:
        params = [by_section[section] for section in candidate.sections if section in by_section]
        params = [param for param in params if param.has_value]
        if not params:
            continue

        new_values: dict[str, float] = {}
        ok = True
        for param in params:
            current = working.get(param.section, param.current)
            room = (param.maximum - current) if candidate.direction > 0 else (current - param.minimum)
            if room <= 1e-9:
                limit_notes.append(
                    f"{param.label} ya está en el límite "
                    f"({format_number(param.display(current), 2)} {param.unit}); "
                    f"no se puede mover más en esa dirección."
                )
                ok = False
                break
            wanted = candidate.steps * param.step
            magnitude = min(wanted, room)
            magnitude = math.floor(magnitude / param.step + 1e-6) * param.step
            if magnitude <= 1e-9:
                limit_notes.append(
                    f"{param.label} no tiene margen para un paso completo de "
                    f"{format_number(param.step_display(), 2)} {param.unit}."
                )
                ok = False
                break
            target = current + candidate.direction * magnitude
            snapped = _snap(param, current, target)
            if abs(snapped - current) < param.step * 0.5:
                ok = False
                break
            new_values[param.section] = snapped
        if not ok or not new_values:
            continue

        before_items = []
        after_items = []
        for section, new_value in new_values.items():
            param = by_section[section]
            old_value = working.get(section, param.current)
            before_items.append(
                {
                    "section": section,
                    "label": param.label,
                    "value": round(param.display(old_value), 4),
                    "unit": param.unit,
                    "file": param.to_file(old_value),
                }
            )
            after_items.append(
                {
                    "section": section,
                    "label": param.label,
                    "value": round(param.display(new_value), 4),
                    "unit": param.unit,
                    "file": param.to_file(new_value),
                }
            )
            file_changes[section] = param.to_file(new_value)
            working[section] = new_value

        delta_display = after_items[0]["value"] - before_items[0]["value"]
        confidence = min(0.92, 0.32 + candidate.score / 3.2)
        changes.append(
            {
                "role": candidate.role,
                "sections": [item["section"] for item in after_items],
                "category": candidate.category,
                "category_label": CATEGORY_LABELS.get(candidate.category, candidate.category),
                "risk": candidate.risk,
                "risk_label": RISK_LABELS.get(candidate.risk, candidate.risk),
                "rules": candidate.rule_id.split("+"),
                "rule_name": candidate.rule_name,
                "reason": candidate.reason,
                "effect": candidate.effect,
                "confidence": round(confidence, 2),
                "confidence_label": "alta" if confidence >= 0.68 else "media" if confidence >= 0.5 else "baja",
                "before": before_items,
                "after": after_items,
                "delta": round(delta_display, 4),
                "delta_unit": after_items[0]["unit"],
                "summary": (
                    f"{after_items[0]['label']}: "
                    f"{format_number(before_items[0]['value'], 2)} → {format_number(after_items[0]['value'], 2)} "
                    f"{after_items[0]['unit']}"
                ),
            }
        )

    new_text = setup.with_values(file_changes)
    return changes, file_changes, new_text, limit_notes


def _missing_data(feedback: FeedbackIn, profile: CarProfile) -> list[str]:
    missing: list[str] = []
    if not feedback.tyre_temps:
        missing.append("Sin temperaturas de neumáticos: el diagnóstico se apoya en tus sensaciones.")
    if not feedback.hot_pressures:
        missing.append("Sin presiones en caliente: no se pueden validar las presiones de trabajo.")
    if feedback.best_lap_ms is None and feedback.avg_lap_ms is None:
        missing.append("Sin tiempos de vuelta: el resultado del test queda a criterio subjetivo.")
    if profile.saved_setups == 0:
        missing.append("Sin setups de referencia de este coche: menor base para comparar.")
    return missing


def _test_plan(
    symptoms: list[SymptomIn], changes: list[dict], context: ContextIn
) -> dict:
    types = {symptom.type for symptom in symptoms}
    watch: list[str] = []
    if "understeer" in types:
        watch.append("Velocidad mínima en el apex y cantidad de corrección de volante.")
    if "oversteer" in types:
        watch.append("Estabilidad de la trasera al soltar el gas y al acelerar.")
    if "wheelspin" in types:
        watch.append("Punto del recorrido en el que podés abrir el gas sin que patine.")
    if "lockup_front" in types or "lockup_rear" in types or "braking_instability" in types:
        watch.append("Trazada y estabilidad en frenada, especialmente al bajar marchas.")
    if "bottoming" in types:
        watch.append("Golpes secos en curvas de compresión y pianos fuertes.")
    if "kerb" in types:
        watch.append("Rebotes y pérdida de contacto al subir pianos.")
    if "top_speed" in types:
        watch.append("Velocidad punta al final de la recta principal.")
    if any(t.startswith("tyre_") for t in types):
        watch.append("Temperaturas interior/centro/exterior después de 4–5 vueltas.")
    if not watch:
        watch.append("Mejor vuelta, promedio de 3 vueltas y sensación general de balance.")

    laps = max(3, context.laps_target)
    procedure = [
        "Guardá el setup actual como referencia y cargá el nuevo en boxes.",
        "Hacé 1 vuelta de calentamiento y después 3 vueltas cronometradas con el mismo compuesto y combustible.",
        "No cambies la técnica de conducción durante el test: misma frenada, misma línea, mismo gas.",
        f"Anotá mejor vuelta, promedio y sensaciones en las mismas curvas ({laps} vueltas objetivo).",
        "Si el coche empeora o se vuelve impredecible, volvé al setup anterior y descartá el paquete.",
    ]
    success = (
        "Mejora la mejor vuelta o el promedio sin perder consistencia, y el síntoma principal baja de intensidad. "
        "Si el tiempo mejora pero el coche se vuelve nervioso, no lo adoptes como base."
    )
    if len(changes) > 1:
        success += " Al ser un paquete de varios cambios, si no hay mejora revertí uno por uno para identificar el culpable."
    return {
        "baseline_laps": 3,
        "test_laps": laps,
        "procedure": procedure,
        "watch": watch,
        "success_criteria": success,
        "conditions": "Mismo compuesto, misma carga de combustible y mismo nivel de goma que la referencia.",
    }


def _explanation(
    car_name: str,
    track_name: str,
    context: ContextIn,
    issues: list[dict],
    changes: list[dict],
    test_plan: dict,
    warnings: list[str],
    driver_notes: str = "",
) -> str:
    condition = {"dry": "seco", "damp": "húmedo", "wet": "mojado"}[context.condition]
    if issues:
        summary = ", ".join(issue["label"] for issue in issues)
        head = f"En {track_name} con el {car_name}, el problema principal es: {summary}. Condición: {condition}."
    else:
        head = f"No cargaste síntomas concretos para {track_name}. Revisemos primero lo básico antes de tocar el setup."
    if driver_notes.strip():
        head += f" El piloto anotó: \"{driver_notes.strip()}\"."

    if changes:
        lines = []
        for change in changes:
            before = change["before"]
            after = change["after"]
            pairs = ", ".join(
                f"{b['label']} {format_number(b['value'], 2)} → {format_number(a['value'], 2)} {a['unit']}"
                for b, a in zip(before, after)
            )
            lines.append(f"- **{change['category_label']}** · {pairs}. {change['reason']}")
        body = "\n".join(lines)
        closers = (
            "Hacé estos cambios y probá en pista. La prioridad es medir, no acumular clics: "
            "si el síntoma no mejora, el problema puede ser de conducción o de otra zona del setup."
        )
    else:
        body = (
            "- No hay cambios numéricos seguros para proponer con los datos actuales. "
            "Cargá temperaturas/presiones y una descripción más concreta por fase (entrada, medio, salida)."
        )
        closers = "Mientras tanto, no toques el setup a ciegas: primero validá presiones y temperaturas."
    warn = ""
    if warnings:
        warn = "\n\n**Antes de probar:** " + " ".join(warnings)
    watch = "\n".join(f"- {item}" for item in test_plan["watch"])
    return (
        f"### Diagnóstico\n{head}\n\n"
        f"### Plan de cambios\n{body}\n\n"
        f"### Cómo probarlo\n{test_plan['conditions']}\n{watch}\n\n"
        f"### Lectura del test\n{test_plan['success_criteria']}{warn}\n\n{closers}"
    )


def analyze(
    setup: SetupFile,
    car_id: str,
    track_id: str,
    setup_name: str,
    setup_path: str | None,
    track_name: str,
    track_type: str,
    context: ContextIn,
    feedback: FeedbackIn,
    use_llm: bool = False,
) -> dict[str, Any]:
    profile = build_profile(car_id, setup)
    kb = load_knowledge()

    tyre_symptoms, tyre_notes = _tyre_symptoms(feedback)
    symptoms = _dedupe_symptoms([*feedback.symptoms, *tyre_symptoms])
    tyre_keys = {(item.type, item.phase, item.speed) for item in tyre_symptoms}
    issues = [
        {
            "type": symptom.type,
            "label": _issue_label(symptom),
            "phase": symptom.phase,
            "phase_label": PHASE_LABELS.get(symptom.phase, symptom.phase),
            "speed": symptom.speed,
            "speed_label": SPEED_LABELS.get(symptom.speed, symptom.speed),
            "severity": symptom.severity,
            "source": "telemetría/temperaturas"
            if (symptom.type, symptom.phase, symptom.speed) in tyre_keys
            else "piloto",
        }
        for symptom in symptoms
    ]
    if not track_type:
        track_type = "balanced"

    candidates = _candidates(profile, symptoms, context, track_type, kb)
    candidates, conflicts = _merge_candidates(candidates, profile)
    max_changes = kb.max_changes_wet if context.condition in ("damp", "wet") else kb.max_changes
    selected = _select(candidates, kb, max_changes)
    changes, file_changes, new_text, limit_notes = _apply_candidates(profile, setup, selected)

    warnings = list(profile.warnings) + tyre_notes + limit_notes
    missing = _missing_data(feedback, profile)
    if context.air_temp_c is not None or context.track_temp_c is not None:
        bits = []
        if context.air_temp_c is not None:
            bits.append(f"aire {context.air_temp_c:.0f}°C")
        if context.track_temp_c is not None:
            bits.append(f"pista {context.track_temp_c:.0f}°C")
        warnings.append("Condiciones térmicas: " + ", ".join(bits) + ".")
    if context.track_temp_c is not None and context.track_temp_c < 20:
        warnings.append(
            "Pista fría: los neumáticos tardarán en entrar en temperatura; "
            "considerá subir las presiones iniciales y hacer una vuelta de calentamiento extra."
        )
    if context.track_temp_c is not None and context.track_temp_c > 45:
        warnings.append(
            "Pista muy caliente: vigilá las presiones en caliente y el desgaste; "
            "probablemente haya que bajar presiones en frío."
        )
    if not symptoms:
        warnings.append("No hay síntomas cargados: el plan es una revisión básica, no un diagnóstico de balance.")
    if conflicts:
        warnings.extend(conflicts)
    warnings = list(dict.fromkeys(warnings))

    test_plan = _test_plan(symptoms, changes, context)
    explanation = _explanation(
        profile.name,
        track_name,
        context,
        issues,
        changes,
        test_plan,
        warnings,
        feedback.notes,
    )
    llm_used = False
    llm_error = None
    if use_llm:
        try:
            from app.llm import narrate

            narrated = narrate(
                {
                    "car": profile.name,
                    "track": track_name,
                    "condition": context.condition,
                    "track_type": track_type,
                    "issues": issues,
                    "changes": changes,
                    "test_plan": test_plan,
                    "warnings": warnings,
                    "driver_notes": feedback.notes,
                }
            )
            if narrated:
                explanation = narrated
                llm_used = True
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)

    return {
        "car": {
            "car_id": car_id,
            "name": profile.name,
            "brand": profile.brand,
            "car_class": profile.car_class,
            "tags": profile.tags,
            "spec_source": profile.spec_source,
            "saved_setups": profile.saved_setups,
        },
        "track": {"track_id": track_id, "name": track_name, "type": track_type},
        "setup": {
            "name": setup_name,
            "path": setup_path,
            "text": setup.text,
            "new_text": new_text,
            "file_changes": file_changes,
            "profile": profile.to_dict(),
        },
        "diagnosis": {
            "summary": (
                " · ".join(issue["label"] for issue in issues)
                if issues
                else "Sin síntomas específicos; revisión básica."
            ),
            "issues": issues,
            "conflicts": conflicts,
            "missing": missing,
        },
        "changes": changes,
        "test_plan": test_plan,
        "explanation": explanation,
        "warnings": warnings,
        "llm_used": llm_used,
        "llm_error": llm_error,
    }
