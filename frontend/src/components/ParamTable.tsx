import { useState } from "react";

import { TAB_LABEL } from "../labels";
import type { CarProfile } from "../types";

function formatNum(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const rounded = Math.round(value * 1000) / 1000;
  return String(rounded);
}

export function ParamTable({ profile }: { profile: CarProfile }) {
  const tabs = Object.keys(profile.groups);
  const [tab, setTab] = useState(tabs[0] ?? "");
  const active = profile.groups[tab] ?? [];

  if (!tabs.length) {
    return <div className="empty">Este setup no tiene parámetros numéricos interpretables.</div>;
  }

  return (
    <div>
      <div className="tabs">
        {tabs.map((key) => (
          <button key={key} className={`tab-btn ${key === tab ? "on" : ""}`} onClick={() => setTab(key)}>
            {TAB_LABEL[key] ?? key}
          </button>
        ))}
      </div>
      <table className="param-table">
        <thead>
          <tr>
            <th>Parámetro</th>
            <th>Valor</th>
            <th>Rango</th>
            <th>Paso</th>
          </tr>
        </thead>
        <tbody>
          {active.map((param) => (
            <tr key={param.section}>
              <td>
                {param.label}
                <span className="muted small"> · {param.section}</span>
                {param.note ? <span className="param-note">{param.note}</span> : null}
              </td>
              <td className="val">
                {formatNum(param.display)} {param.unit}
              </td>
              <td className="rng">
                {formatNum(param.min_display)} – {formatNum(param.max_display)}
              </td>
              <td className="rng">±{formatNum(param.step_display)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProfileSummary({ profile }: { profile: CarProfile }) {
  const withValue = profile.params.filter((p) => p.has_value).length;
  return (
    <div className="row" style={{ gap: 8 }}>
      <span className="chip cyan">{profile.car_class.toUpperCase()}</span>
      <span className="chip">{withValue} parámetros activos</span>
      <span className="chip">
        {profile.spec_available ? `Límites: ${profile.spec_source}` : "Límites inferidos"}
      </span>
      {profile.saved_setups > 0 ? (
        <span className="chip ok">{profile.saved_setups} setups de referencia</span>
      ) : (
        <span className="chip warn">Sin setups de referencia</span>
      )}
      {profile.warnings.length > 0 ? (
        <span className="chip warn">{profile.warnings.length} aviso(s)</span>
      ) : null}
    </div>
  );
}
