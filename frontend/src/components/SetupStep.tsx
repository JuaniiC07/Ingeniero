import { useMemo, useState } from "react";

import { ProfileSummary, ParamTable } from "./ParamTable";
import { formatLap, TRACK_TYPE_LABEL } from "../labels";
import type { Catalog, InspectResponse } from "../types";

interface Props {
  catalog: Catalog;
  carId: string | null;
  trackId: string | null;
  setupPath: string | null;
  inspect: InspectResponse | null;
  mode: "saved" | "paste";
  customText: string;
  busy: boolean;
  error: string | null;
  sessionId: number | null;
  onCar: (id: string) => void;
  onTrack: (id: string) => void;
  onSetup: (path: string) => void;
  onMode: (mode: "saved" | "paste") => void;
  onCustomText: (text: string) => void;
  onInspectText: () => void;
  onRefresh: () => void;
  onNext: () => void;
  onCreateSession: () => void;
}

export function SetupStep(props: Props) {
  const { catalog } = props;
  const [query, setQuery] = useState("");
  const [showAllTracks, setShowAllTracks] = useState(false);

  const cars = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return catalog.cars
      .filter((car) => !needle || `${car.name} ${car.brand} ${car.car_id}`.toLowerCase().includes(needle))
      .sort((a, b) => {
        const aRace = a.car_class === "gt3" || a.car_class === "formula" ? 0 : 1;
        const bRace = b.car_class === "gt3" || b.car_class === "formula" ? 0 : 1;
        return aRace - bRace || a.name.localeCompare(b.name);
      });
  }, [catalog.cars, query]);

  const setups = useMemo(() => {
    if (!props.carId) return [];
    let list = catalog.setups.filter((setup) => setup.car_id === props.carId);
    if (props.trackId && !showAllTracks) {
      const filtered = list.filter((setup) => setup.track_id === props.trackId);
      if (filtered.length > 0) list = filtered;
    }
    return list.sort((a, b) => b.modified.localeCompare(a.modified));
  }, [catalog.setups, props.carId, props.trackId, showAllTracks]);

  const trackName = (id: string) =>
    catalog.tracks.find((track) => track.track_id === id)?.name ?? id;

  const selectedCar = catalog.cars.find((car) => car.car_id === props.carId) ?? null;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <section className="card">
        <div className="card-head">
          <div>
            <div className="card-title">1 · Elegí el coche</div>
            <div className="card-sub">
              {catalog.counts.cars} coches detectados en tu instalación de Assetto Corsa.
            </div>
          </div>
          <button className="btn small ghost" onClick={props.onRefresh} disabled={props.busy}>
            Re-escanear
          </button>
        </div>

        <input
          className="input"
          placeholder="Buscar coche por nombre, marca o id…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          style={{ marginBottom: 12 }}
        />

        <div className="car-grid">
          {cars.slice(0, 400).map((car) => (
            <button
              key={car.car_id}
              className={`pick-card ${car.car_id === props.carId ? "selected" : ""}`}
              onClick={() => props.onCar(car.car_id)}
            >
              <span className="pc-name">{car.name}</span>
              <span className="pc-meta">
                <span>{car.brand || car.car_id}</span>
                <span>· {car.car_class.toUpperCase()}</span>
                {car.saved_setups > 0 ? <span>· {car.saved_setups} setups</span> : null}
                {!car.has_profile ? <span style={{ color: "var(--warn)" }}>· sin data.acd</span> : null}
              </span>
            </button>
          ))}
          {cars.length === 0 ? <div className="empty">Ningún coche coincide con “{query}”.</div> : null}
        </div>
      </section>

      {selectedCar ? (
        <section className="card">
          <div className="card-head">
            <div>
              <div className="card-title">2 · Circuito y setup base</div>
              <div className="card-sub">
                El setup base nunca se modifica: la app genera un archivo nuevo.
              </div>
            </div>
          </div>

          <div className="grid two" style={{ marginBottom: 16 }}>
            <div className="field">
              <label>Circuito</label>
              <select
                className="select"
                value={props.trackId ?? ""}
                onChange={(event) => props.onTrack(event.target.value)}
              >
                <option value="">Sin circuito específico</option>
                {catalog.tracks.map((track) => (
                  <option key={track.track_id} value={track.track_id}>
                    {track.name} — {TRACK_TYPE_LABEL[track.type] ?? track.type}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Origen del setup</label>
              <div className="seg">
                <button className={props.mode === "saved" ? "on" : ""} onClick={() => props.onMode("saved")}>
                  Setup guardado
                </button>
                <button className={props.mode === "paste" ? "on" : ""} onClick={() => props.onMode("paste")}>
                  Pegar / importar .ini
                </button>
              </div>
            </div>
          </div>

          {props.mode === "saved" ? (
            <div>
              {props.trackId ? (
                <div className="row" style={{ marginBottom: 8 }}>
                  <span className="muted small">
                    {showAllTracks ? "Mostrando todos los circuitos." : "Filtrado por el circuito elegido."}
                  </span>
                  <span className="spacer" />
                  <button className="btn small ghost" onClick={() => setShowAllTracks((v) => !v)}>
                    {showAllTracks ? "Filtrar por circuito" : "Mostrar todos"}
                  </button>
                </div>
              ) : null}
              <div className="setup-list">
                {setups.map((setup) => (
                  <button
                    key={setup.id}
                    className={`setup-row ${setup.path === props.setupPath ? "selected" : ""}`}
                    onClick={() => props.onSetup(setup.path)}
                  >
                    <div style={{ flex: 1 }}>
                      <div className="sr-name">
                        {setup.name}
                        {setup.generated ? <span className="chip accent" style={{ marginLeft: 8 }}>ENG</span> : null}
                      </div>
                      <div className="sr-track">
                        {trackName(setup.track_id)} · {setup.file_name}
                      </div>
                    </div>
                    {setup.lap_ms !== null ? (
                      <span className="chip ok mono">{formatLap(setup.lap_ms)}</span>
                    ) : null}
                  </button>
                ))}
                {setups.length === 0 ? (
                  <div className="empty">
                    No hay setups guardados de este coche para este filtro. Cambiá a "Pegar / importar .ini" o "Mostrar todos".
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="field">
              <label>Contenido del archivo .ini</label>
              <textarea
                className="textarea mono"
                style={{ minHeight: 200 }}
                placeholder={"[PRESSURE_LF]\nVALUE=19\n\n[ARB_FRONT]\nVALUE=40000\n…"}
                value={props.customText}
                onChange={(event) => props.onCustomText(event.target.value)}
              />
              <div className="row">
                <button
                  className="btn small"
                  onClick={props.onInspectText}
                  disabled={props.busy || props.customText.trim().length < 10}
                >
                  Analizar este setup
                </button>
                <span className="muted small">
                  Se detecta el coche desde la sección [CAR] MODEL= cuando está presente.
                </span>
              </div>
            </div>
          )}

          {props.error ? <div className="callout bad" style={{ marginTop: 12 }}>{props.error}</div> : null}
        </section>
      ) : null}

      {props.inspect ? (
        <section className="card">
          <div className="card-head">
            <div>
              <div className="card-title">
                {props.inspect.car.name}
                <span className="muted" style={{ fontWeight: 400 }}>
                  {" "}
                  · {props.inspect.track.name}
                </span>
              </div>
              <div className="card-sub">
                Setup cargado: <strong>{props.inspect.setup.name}</strong>
                {props.inspect.setup.path ? ` · ${props.inspect.setup.path}` : " · importado"}
              </div>
            </div>
            <div className="row">
              {props.inspect && !props.sessionId ? (
                <button className="btn small ghost" onClick={props.onCreateSession} disabled={props.busy}>
                  + Crear sesión
                </button>
              ) : null}
              {props.sessionId ? <span className="chip ok">Sesión #{props.sessionId}</span> : null}
              <button className="btn primary" onClick={props.onNext}>
                Continuar al contexto →
              </button>
            </div>
          </div>

          <ProfileSummary profile={props.inspect.profile} />

          {props.inspect.warnings.length > 0 ? (
            <div style={{ marginTop: 12 }}>
              {props.inspect.warnings.map((warning) => (
                <div className="callout warn" key={warning}>
                  {warning}
                </div>
              ))}
            </div>
          ) : null}

          <div style={{ marginTop: 16 }}>
            <ParamTable profile={props.inspect.profile} />
          </div>
        </section>
      ) : null}
    </div>
  );
}
