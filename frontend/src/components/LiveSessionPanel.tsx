import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import { formatLap } from "../labels";
import type { InspectResponse } from "../types";

interface LapEntry {
  lap: number;
  timeMs: number;
  sectorMs: number | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  inspect: InspectResponse | null;
  onUseData: (data: Record<string, unknown>) => void;
}

export function LiveSessionPanel({ open, onClose, inspect, onUseData }: Props) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [laps, setLaps] = useState<LapEntry[]>([]);
  const lastCompletedRef = useRef<number>(0);
  const lastLapTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    const poll = async () => {
      try {
        const d = (await api.acLive()) as Record<string, unknown>;
        if (!alive) return;
        setData(d);
        setError(null);
        const completed = typeof d.completed_laps === "number" ? (d.completed_laps as number) : 0;
        const last = typeof d.last_lap_ms === "number" ? (d.last_lap_ms as number) : null;
        if (completed > lastCompletedRef.current && last && last !== lastLapTimeRef.current) {
          setLaps((prev) => [
            ...prev,
            { lap: completed, timeMs: last, sectorMs: typeof d.lastSectorTime === "number" ? (d.lastSectorTime as number) : null },
          ]);
          lastCompletedRef.current = completed;
          lastLapTimeRef.current = last;
        }
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : String(err));
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [open]);

  if (!open) return null;

  const status = typeof data?.status === "string" ? (data.status as string) : "—";
  const live = status === "live";
  const temps = data?.tyre_temps as Record<string, { inner?: number; middle?: number; outer?: number }> | undefined;
  const pressures = data?.tyre_pressures as Record<string, number> | undefined;
  const wear = data?.tyre_wear as Record<string, number> | undefined;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" style={{ width: "min(720px, 100%)" }} onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <div className="card-title">Sesión en vivo de Assetto Corsa</div>
            <div className="card-sub">
              {live ? "En pista — datos en tiempo real." : `Estado: ${status}. Entrá a pista para leer datos.`}
            </div>
          </div>
          {data ? (
            <button className="btn small primary" onClick={() => onUseData(data)}>
              Usar estos datos
            </button>
          ) : null}
          <button className="btn small ghost" onClick={onClose}>
            Cerrar ✕
          </button>
        </div>
        <div className="drawer-body">
          {error ? <div className="callout bad">{error}</div> : null}
          {!data ? <div className="empty">Conectando…</div> : null}

          {data ? (
            <>
              <div className="grid two" style={{ marginBottom: 12 }}>
                <div className="card" style={{ padding: 12 }}>
                  <div className="section-label">Sesión</div>
                  <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
                    <span className="chip cyan">{String(data.car_id ?? "—")}</span>
                    <span className="chip">{String(data.track_id ?? "—")}</span>
                    <span className="chip">{String(data.session_type ?? "—")}</span>
                    {data.tyre_compound ? <span className="chip">{String(data.tyre_compound)}</span> : null}
                  </div>
                  <div className="muted small" style={{ marginTop: 8 }}>
                    Aire {Number(data.air_temp_c ?? 0).toFixed(1)}°C · Pista {Number(data.road_temp_c ?? 0).toFixed(1)}°C ·
                    Grip {typeof data.surface_grip === "number" ? Math.round((data.surface_grip as number) * 100) : "—"} ·
                    Combustible {Number(data.fuel_l ?? 0).toFixed(1)} L
                  </div>
                </div>
                <div className="card" style={{ padding: 12 }}>
                  <div className="section-label">Tiempos</div>
                  <div className="change-delta">
                    <span style={{ fontFamily: "inherit" }}>Vuelta actual</span>
                    <span className="delta-new">{formatLap(typeof data.current_lap_ms === "number" ? (data.current_lap_ms as number) : null)}</span>
                  </div>
                  <div className="change-delta">
                    <span style={{ fontFamily: "inherit" }}>Última vuelta</span>
                    <span>{formatLap(typeof data.last_lap_ms === "number" ? (data.last_lap_ms as number) : null)}</span>
                  </div>
                  <div className="change-delta">
                    <span style={{ fontFamily: "inherit" }}>Mejor vuelta</span>
                    <span className="delta-new">{formatLap(typeof data.best_lap_ms === "number" ? (data.best_lap_ms as number) : null)}</span>
                  </div>
                  <div className="muted small" style={{ marginTop: 6 }}>
                    Vueltas completadas: {String(data.completed_laps ?? 0)} · Sector actual: {String(data.currentSectorIndex ?? "—")} ·
                    Último sector: {formatLap(typeof data.lastSectorTime === "number" ? (data.lastSectorTime as number) : null)}
                  </div>
                </div>
              </div>

              <div className="section-label">Neumáticos en vivo</div>
              <table className="param-table" style={{ marginBottom: 12 }}>
                <thead>
                  <tr>
                    <th>Rueda</th>
                    <th>Int/Med/Ext °C</th>
                    <th>Presión</th>
                    <th>Desgaste</th>
                  </tr>
                </thead>
                <tbody>
                  {(["lf", "rf", "lr", "rr"] as const).map((k) => (
                    <tr key={k}>
                      <td className="val">{k.toUpperCase()}</td>
                      <td>
                        {temps?.[k]?.inner?.toFixed(0) ?? "—"} / {temps?.[k]?.middle?.toFixed(0) ?? "—"} /{" "}
                        {temps?.[k]?.outer?.toFixed(0) ?? "—"}
                      </td>
                      <td className="val">{pressures?.[k]?.toFixed(1) ?? "—"} psi</td>
                      <td>{wear?.[k]?.toFixed(0) ?? "—"}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="section-label">Tabla de vueltas (esta sesión)</div>
              {laps.length === 0 ? (
                <div className="empty">Completá una vuelta para que aparezca aquí.</div>
              ) : (
                <table className="param-table">
                  <thead>
                    <tr>
                      <th>Vuelta</th>
                      <th>Tiempo</th>
                      <th>Último sector</th>
                    </tr>
                  </thead>
                  <tbody>
                    {laps.map((entry) => (
                      <tr key={entry.lap}>
                        <td className="val">{entry.lap}</td>
                        <td className="val">{formatLap(entry.timeMs)}</td>
                        <td>{entry.sectorMs !== null ? formatLap(entry.sectorMs) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {inspect ? (
                <div style={{ marginTop: 12 }}>
                  <div className="section-label">Setup en desarrollo</div>
                  <div className="muted small">
                    {inspect.car.name} · {inspect.setup.name}
                    {inspect.setup.path ? ` · ${inspect.setup.path}` : ""}
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
