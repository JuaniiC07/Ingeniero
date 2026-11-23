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
  inspect: InspectResponse | null;
  onUseData: () => void;
}

export function LiveSessionView({ inspect, onUseData }: Props) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [laps, setLaps] = useState<LapEntry[]>([]);
  const lastCompletedRef = useRef<number>(0);
  const lastLapTimeRef = useRef<number | null>(null);

  useEffect(() => {
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
  }, []);

  const status = typeof data?.status === "string" ? (data.status as string) : "—";
  const live = status === "live";
  const temps = data?.tyre_temps as Record<string, { inner?: number; middle?: number; outer?: number }> | undefined;
  const pressures = data?.tyre_pressures as Record<string, number> | undefined;
  const wear = data?.tyre_wear as Record<string, number> | undefined;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title" style={{ fontSize: 18 }}>
              Sesión en vivo
              <span className={`chip ${live ? "ok" : "warn"}`} style={{ marginLeft: 10 }}>
                {live ? "● EN PISTA" : status.toUpperCase()}
              </span>
            </div>
            <div className="card-sub">
              Datos en tiempo real desde la memoria compartida de Assetto Corsa. Se actualiza cada segundo.
            </div>
          </div>
          <div className="row">
            {data ? (
              <button className="btn primary" onClick={onUseData}>
                Usar estos datos en el análisis
              </button>
            ) : null}
          </div>
        </div>
        {error ? <div className="callout bad">{error}</div> : null}
        {!data ? <div className="empty">Conectando con Assetto Corsa…</div> : null}
      </section>

      {data ? (
        <>
          <div className="grid two">
            <section className="card">
              <div className="section-label">Sesión</div>
              <div className="row" style={{ gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
                <span className="chip cyan">{String(data.car_id ?? "—")}</span>
                <span className="chip">{String(data.track_id ?? "—")}</span>
                <span className="chip">{String(data.session_type ?? "—")}</span>
                {data.track_config && data.track_config !== "layout_24h_2024" ? (
                  <span className="chip">{String(data.track_config)}</span>
                ) : null}
                {data.tyre_compound ? <span className="chip">{String(data.tyre_compound)}</span> : null}
              </div>
              <div className="grid two">
                <div>
                  <div className="section-label">Ambiente</div>
                  <div className="muted small">
                    Aire <strong>{Number(data.air_temp_c ?? 0).toFixed(1)}°C</strong>
                  </div>
                  <div className="muted small">
                    Pista <strong>{Number(data.road_temp_c ?? 0).toFixed(1)}°C</strong>
                  </div>
                  <div className="muted small">
                    Grip <strong>{typeof data.surface_grip === "number" ? Math.round((data.surface_grip as number) * 100) : "—"}%</strong>
                  </div>
                  <div className="muted small">
                    Combustible <strong>{Number(data.fuel_l ?? 0).toFixed(1)} L</strong>
                  </div>
                </div>
                <div>
                  <div className="section-label">Piloto</div>
                  <div className="muted small">{String(data.player ?? "—")}</div>
                  <div className="muted small">Vueltas completadas: {String(data.completed_laps ?? 0)}</div>
                </div>
              </div>
            </section>

            <section className="card">
              <div className="section-label">Tiempos</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="change-delta">
                  <span style={{ fontFamily: "inherit", flex: 1 }}>Vuelta actual</span>
                  <span className="delta-new" style={{ fontSize: 18 }}>{formatLap(typeof data.current_lap_ms === "number" ? (data.current_lap_ms as number) : null)}</span>
                </div>
                <div className="change-delta">
                  <span style={{ fontFamily: "inherit", flex: 1 }}>Última vuelta</span>
                  <span>{formatLap(typeof data.last_lap_ms === "number" ? (data.last_lap_ms as number) : null)}</span>
                </div>
                <div className="change-delta">
                  <span style={{ fontFamily: "inherit", flex: 1 }}>Mejor vuelta</span>
                  <span className="delta-new">{formatLap(typeof data.best_lap_ms === "number" ? (data.best_lap_ms as number) : null)}</span>
                </div>
              </div>
              <div className="muted small" style={{ marginTop: 10 }}>
                Sector actual: {String(data.currentSectorIndex ?? "—")} · Último sector:{" "}
                {formatLap(typeof data.lastSectorTime === "number" ? (data.lastSectorTime as number) : null)}
              </div>
            </section>
          </div>

          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Neumáticos en vivo</div>
                <div className="card-sub">Temperaturas interior / centro / exterior, presión y desgaste.</div>
              </div>
            </div>
            <table className="param-table">
              <thead>
                <tr>
                  <th>Rueda</th>
                  <th>Temp. I/M/E (°C)</th>
                  <th>Presión (psi)</th>
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
          </section>

          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Tabla de vueltas</div>
                <div className="card-sub">Se registra automáticamente cada vuelta completada.</div>
              </div>
              {laps.length > 0 ? (
                <button className="btn small ghost" onClick={() => setLaps([])}>
                  Limpiar
                </button>
              ) : null}
            </div>
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
          </section>

          {inspect ? (
            <section className="card">
              <div className="section-label">Setup en desarrollo</div>
              <div className="muted small">
                {inspect.car.name} · {inspect.setup.name}
                {inspect.setup.path ? ` · ${inspect.setup.path}` : ""}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
