import { useMemo } from "react";

import { PHASE_LABEL, SPEED_LABEL, SYMPTOMS, SYMPTOM_BY_TYPE, parseLap } from "../labels";
import type { FeedbackPayload, Phase, Speed, Symptom, TyreKey, TyreTemp } from "../types";

interface Props {
  feedback: FeedbackPayload;
  onChange: (patch: Partial<FeedbackPayload>) => void;
  onBack: () => void;
  onAnalyze: () => void;
  busy: boolean;
  error: string | null;
  useLlm: boolean;
  setUseLlm: (value: boolean) => void;
  llmReady: boolean;
  llmModel: string | null;
}

const EMPTY_TYRE: TyreTemp = { inner: null, middle: null, outer: null };
const TYRE_KEYS: TyreKey[] = ["lf", "rf", "lr", "rr"];
const TYRE_LABEL: Record<TyreKey, string> = { lf: "Delantera izq.", rf: "Delantera der.", lr: "Trasera izq.", rr: "Trasera der." };

function num(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

export function FeedbackStep(props: Props) {
  const { feedback, onChange } = props;

  const selected = useMemo(() => new Map(feedback.symptoms.map((item) => [item.type, item])), [feedback.symptoms]);

  const groups = useMemo(() => {
    const map = new Map<string, typeof SYMPTOMS>();
    for (const item of SYMPTOMS) {
      const list = map.get(item.group) ?? [];
      list.push(item);
      map.set(item.group, list);
    }
    return Array.from(map.entries());
  }, []);

  const toggle = (type: Symptom["type"]) => {
    if (selected.has(type)) {
      onChange({ symptoms: feedback.symptoms.filter((item) => item.type !== type) });
      return;
    }
    const def = SYMPTOM_BY_TYPE[type];
    const symptom: Symptom = {
      type,
      phase: def.phases[0],
      speed: def.speeds.includes("any") ? "any" : def.speeds[0],
      severity: 2,
    };
    onChange({ symptoms: [...feedback.symptoms, symptom] });
  };

  const patchSymptom = (type: Symptom["type"], patch: Partial<Symptom>) => {
    onChange({
      symptoms: feedback.symptoms.map((item) => (item.type === type ? { ...item, ...patch } : item)),
    });
  };

  const tyreTemps: Partial<Record<TyreKey, TyreTemp>> = feedback.tyre_temps ?? {};
  const pressures: Partial<Record<TyreKey, number>> = feedback.hot_pressures ?? {};

  const setTyre = (key: TyreKey, field: keyof TyreTemp, value: number | null) => {
    const next = { ...tyreTemps, [key]: { ...(tyreTemps[key] ?? EMPTY_TYRE), [field]: value } };
    onChange({ tyre_temps: next });
  };

  const setPressure = (key: TyreKey, value: number | null) => {
    const next = { ...pressures };
    if (value === null) delete next[key];
    else next[key] = value;
    onChange({ hot_pressures: Object.keys(next).length ? next : null });
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">¿Qué hace el coche?</div>
            <div className="card-sub">
              Marcá los síntomas y ajustá en qué fase aparece. La severidad modula la magnitud del cambio.
            </div>
          </div>
          <span className="chip accent">{feedback.symptoms.length} seleccionados</span>
        </div>

        {groups.map(([group, items]) => (
          <div className="symptom-group" key={group}>
            <div className="section-label">{group}</div>
            <div className="symptom-grid">
              {items.map((def) => {
                const active = selected.get(def.type);
                return (
                  <button
                    key={def.type}
                    className={`symptom-card ${active ? "selected" : ""}`}
                    onClick={() => toggle(def.type)}
                  >
                    <span className="symptom-check">✓</span>
                    <span className="symptom-body">
                      <strong>{def.label}</strong>
                      <span>{def.hint}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </section>

      {feedback.symptoms.length > 0 ? (
        <section className="card">
          <div className="card-head">
            <div>
              <div className="card-title">Detalle de cada síntoma</div>
              <div className="card-sub">Fase y velocidad donde más se nota. “General” aplica a todo.</div>
            </div>
          </div>
          <div className="grid" style={{ gap: 10 }}>
            {feedback.symptoms.map((symptom) => {
              const def = SYMPTOM_BY_TYPE[symptom.type];
              if (!def) return null;
              return (
                <div className="symptom-config" key={symptom.type}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <strong style={{ fontSize: 13 }}>{def.label}</strong>
                    <button className="btn small ghost danger" onClick={() => toggle(symptom.type)}>
                      Quitar
                    </button>
                  </div>
                  <div className="row">
                    <div className="field">
                      <label>Fase</label>
                      <div className="seg tiny">
                        {def.phases.map((phase) => (
                          <button
                            key={phase}
                            className={symptom.phase === phase ? "on" : ""}
                            onClick={() => patchSymptom(symptom.type, { phase: phase as Phase })}
                          >
                            {PHASE_LABEL[phase]}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="field">
                      <label>Velocidad</label>
                      <div className="seg tiny">
                        {def.speeds.map((speed) => (
                          <button
                            key={speed}
                            className={symptom.speed === speed ? "on" : ""}
                            onClick={() => patchSymptom(symptom.type, { speed: speed as Speed })}
                          >
                            {SPEED_LABEL[speed]}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="field">
                      <label>Severidad</label>
                      <div className="seg tiny">
                        {[1, 2, 3].map((level) => (
                          <button
                            key={level}
                            className={symptom.severity === level ? "on" : ""}
                            onClick={() => patchSymptom(symptom.type, { severity: level })}
                          >
                            {level === 1 ? "Leve" : level === 2 ? "Media" : "Fuerte"}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Temperaturas y presiones en caliente</div>
            <div className="card-sub">
              Opcional. Se usan para detectar camber/presión y proponer cambios de alineación.
            </div>
          </div>
        </div>

        <div className="tyre-grid">
          {TYRE_KEYS.map((key) => {
            const tyre = tyreTemps[key] ?? EMPTY_TYRE;
            return (
              <div className="tyre-box" key={key}>
                <div className="tb-head">
                  <span>{TYRE_LABEL[key]}</span>
                  <span className="muted small">psi caliente</span>
                </div>
                <div className="tyre-inputs">
                  <div className="field">
                    <label>Interior</label>
                    <input
                      className="input"
                      type="number"
                      value={tyre.inner ?? ""}
                      onChange={(event) => setTyre(key, "inner", num(event.target.value))}
                    />
                  </div>
                  <div className="field">
                    <label>Centro</label>
                    <input
                      className="input"
                      type="number"
                      value={tyre.middle ?? ""}
                      onChange={(event) => setTyre(key, "middle", num(event.target.value))}
                    />
                  </div>
                  <div className="field">
                    <label>Exterior</label>
                    <input
                      className="input"
                      type="number"
                      value={tyre.outer ?? ""}
                      onChange={(event) => setTyre(key, "outer", num(event.target.value))}
                    />
                  </div>
                </div>
                <div className="field" style={{ marginTop: 8 }}>
                  <label>Presión</label>
                  <input
                    className="input"
                    type="number"
                    step="0.1"
                    value={pressures[key] ?? ""}
                    placeholder="—"
                    onChange={(event) => setPressure(key, num(event.target.value))}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Tiempos y notas</div>
            <div className="card-sub">Los tiempos permiten comparar el resultado del test más adelante.</div>
          </div>
        </div>

        <div className="grid three">
          <div className="field">
            <label>Mejor vuelta (m:ss.mmm)</label>
            <input
              className="input"
              placeholder="2:14.300"
              defaultValue={feedback.best_lap_ms ? (feedback.best_lap_ms / 1000).toFixed(3) : ""}
              onBlur={(event) => onChange({ best_lap_ms: parseLap(event.target.value) })}
            />
          </div>
          <div className="field">
            <label>Promedio de 3 vueltas</label>
            <input
              className="input"
              placeholder="2:15.100"
              defaultValue={feedback.avg_lap_ms ? (feedback.avg_lap_ms / 1000).toFixed(3) : ""}
              onBlur={(event) => onChange({ avg_lap_ms: parseLap(event.target.value) })}
            />
          </div>
          <div className="field">
            <label>Vueltas completadas</label>
            <input
              className="input"
              type="number"
              min={0}
              value={feedback.laps_completed ?? ""}
              onChange={(event) => onChange({ laps_completed: num(event.target.value) })}
            />
          </div>
        </div>

        <div className="field" style={{ marginTop: 14 }}>
          <label>Notas del piloto</label>
          <textarea
            className="textarea"
            placeholder="Ej.: en la curva 3 se va de morro al soltar el freno; en la salida de la 10 patina si abro antes del vértice…"
            value={feedback.notes}
            onChange={(event) => onChange({ notes: event.target.value })}
          />
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Explicación</div>
            <div className="card-sub">
              La plantilla determinística siempre está disponible. El modelo local solo redacta, nunca inventa valores.
            </div>
          </div>
        </div>

        <label className="row" style={{ cursor: props.llmReady ? "pointer" : "not-allowed", gap: 10 }}>
          <input
            type="checkbox"
            checked={props.useLlm}
            disabled={!props.llmReady}
            onChange={(event) => props.setUseLlm(event.target.checked)}
            style={{ width: 16, height: 16, accentColor: "var(--accent)" }}
          />
          <span style={{ fontSize: 13 }}>
            Redactar con Ollama {props.llmReady ? `(${props.llmModel})` : "— no detectado"}
          </span>
        </label>
        {!props.llmReady ? (
          <div className="callout" style={{ marginTop: 10 }}>
            Ollama no está corriendo. La explicación se genera con la plantilla del ingeniero, sin costo ni
            conexión.
          </div>
        ) : null}
      </section>

      {props.error ? <div className="callout bad">{props.error}</div> : null}

      <div className="row end">
        <button className="btn ghost" onClick={props.onBack}>
          ← Volver
        </button>
        <button className="btn primary" onClick={props.onAnalyze} disabled={props.busy}>
          {props.busy ? "Analizando…" : "Generar diagnóstico →"}
        </button>
      </div>
    </div>
  );
}
