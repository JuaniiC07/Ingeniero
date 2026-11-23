import { CONDITION_LABEL, SESSION_LABEL, TRACK_TYPE_LABEL } from "../labels";
import type { ContextPayload, InspectResponse } from "../types";

interface Props {
  inspect: InspectResponse;
  context: ContextPayload;
  onChange: (patch: Partial<ContextPayload>) => void;
  onBack: () => void;
  onNext: () => void;
}

const TRACK_TYPES = ["fast", "technical", "bumpy", "street", "oval", "balanced"];

export function ContextStep({ inspect, context, onChange, onBack, onNext }: Props) {
  return (
    <div className="grid" style={{ gap: 16 }}>
      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Condiciones de la sesión</div>
            <div className="card-sub">
              {inspect.car.name} en {inspect.track.name}. Estos datos ajustan la agresividad del plan.
            </div>
          </div>
        </div>

        <div className="grid two">
          <div className="field">
            <label>Estado de la pista</label>
            <div className="seg">
              {(Object.keys(CONDITION_LABEL) as Array<keyof typeof CONDITION_LABEL>).map((key) => (
                <button
                  key={key}
                  className={context.condition === key ? "on" : ""}
                  onClick={() => onChange({ condition: key })}
                >
                  {CONDITION_LABEL[key]}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Tipo de sesión</label>
            <div className="seg">
              {(Object.keys(SESSION_LABEL) as Array<keyof typeof SESSION_LABEL>).map((key) => (
                <button
                  key={key}
                  className={context.session_type === key ? "on" : ""}
                  onClick={() => onChange({ session_type: key })}
                >
                  {SESSION_LABEL[key]}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Tipo de circuito (detectado, editable)</label>
            <select
              className="select"
              value={context.track_type ?? inspect.track.type}
              onChange={(event) => onChange({ track_type: event.target.value })}
            >
              {TRACK_TYPES.map((type) => (
                <option key={type} value={type}>
                  {TRACK_TYPE_LABEL[type] ?? type}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>Vueltas objetivo del test</label>
            <input
              className="input"
              type="number"
              min={1}
              max={60}
              value={context.laps_target}
              onChange={(event) => onChange({ laps_target: Math.max(1, Number(event.target.value) || 1) })}
            />
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Ambiente y combustible</div>
            <div className="card-sub">Opcional, pero mejora la lectura de presiones y temperaturas.</div>
          </div>
        </div>

        <div className="grid three">
          <div className="field">
            <label>Temperatura aire (°C)</label>
            <input
              className="input"
              type="number"
              value={context.air_temp_c ?? ""}
              placeholder="22"
              onChange={(event) => onChange({ air_temp_c: event.target.value === "" ? null : Number(event.target.value) })}
            />
          </div>
          <div className="field">
            <label>Temperatura pista (°C)</label>
            <input
              className="input"
              type="number"
              value={context.track_temp_c ?? ""}
              placeholder="30"
              onChange={(event) => onChange({ track_temp_c: event.target.value === "" ? null : Number(event.target.value) })}
            />
          </div>
          <div className="field">
            <label>Nivel de goma (0-100)</label>
            <input
              className="input"
              type="number"
              min={0}
              max={100}
              value={context.grip ?? ""}
              placeholder="95"
              onChange={(event) => onChange({ grip: event.target.value === "" ? null : Number(event.target.value) })}
            />
          </div>
          <div className="field">
            <label>Combustible (L)</label>
            <input
              className="input"
              type="number"
              value={context.fuel_l ?? ""}
              placeholder="60"
              onChange={(event) => onChange({ fuel_l: event.target.value === "" ? null : Number(event.target.value) })}
            />
          </div>
          <div className="field">
            <label>Compuesto</label>
            <input
              className="input"
              value={context.compound ?? ""}
              placeholder="Slick / Medium"
              onChange={(event) => onChange({ compound: event.target.value || null })}
            />
          </div>
        </div>
      </section>

      <div className="row end">
        <button className="btn ghost" onClick={onBack}>
          ← Volver
        </button>
        <button className="btn primary" onClick={onNext}>
          Continuar a sensaciones →
        </button>
      </div>
    </div>
  );
}
