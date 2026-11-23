import { useMemo, useState } from "react";

import { diffLines } from "../diff";
import { formatNumber } from "../labels";
import type { AnalyzeResponse, ChangeItem } from "../types";

interface Props {
  analysis: AnalyzeResponse;
  onBack: () => void;
  onSave: (name: string) => void;
  saving: boolean;
  savedPath: string | null;
  onResult: (outcome: "better" | "same" | "worse" | "unknown", notes: string, bestLapMs: number | null) => void;
  resultSaved: boolean;
  onNarrate: () => void;
  narrating: boolean;
  llmReady: boolean;
  sessionId: number | null;
  onContinueSession: () => void;
}

function RiskMeter({ risk }: { risk: string }) {
  const level = risk === "high" ? 3 : risk === "medium" ? 2 : 1;
  return (
    <span className="risk-meter" title={`Riesgo ${risk}`}>
      {[1, 2, 3].map((index) => (
        <i key={index} className={`${index <= level ? `on ${risk}` : ""}`} />
      ))}
    </span>
  );
}

function ChangeCard({ change }: { change: ChangeItem }) {
  return (
    <div className="change-card">
      <div className="change-top">
        <span className="chip accent">{change.category_label}</span>
        <span className="ct-title">{change.rule_name}</span>
        <span className="spacer" />
        <RiskMeter risk={change.risk} />
        <span className={`chip ${change.confidence >= 0.68 ? "ok" : change.confidence >= 0.5 ? "" : "warn"}`}>
          Confianza {change.confidence_label}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {change.before.map((before, index) => {
          const after = change.after[index];
          if (!after) return null;
          return (
            <div className="change-delta" key={before.section}>
              <span style={{ color: "var(--text-dim)", fontFamily: "inherit", fontSize: 12.5 }}>{before.label}</span>
              <span className="delta-old">{formatNumber(before.value)}</span>
              <span className="delta-arrow">→</span>
              <span className="delta-new">{formatNumber(after.value)}</span>
              <span className="delta-unit">{after.unit}</span>
              {after.unit === "click" && before.file !== after.file ? (
                <span className="delta-unit">(archivo: {before.file} → {after.file})</span>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="change-text">
        <strong>Por qué:</strong> {change.reason}
      </div>
      <div className="change-text">
        <strong>Qué esperar:</strong> {change.effect}
      </div>
    </div>
  );
}

export function DiagnosisStep(props: Props) {
  const { analysis } = props;
  const [name, setName] = useState("");
  const [outcome, setOutcome] = useState<"better" | "same" | "worse" | "unknown">("unknown");
  const [resultNotes, setResultNotes] = useState("");
  const [bestLap, setBestLap] = useState("");

  const diff = useMemo(
    () => diffLines(analysis.setup.text, analysis.setup.new_text),
    [analysis.setup.text, analysis.setup.new_text],
  );
  const changed = diff.filter((line) => line.type !== "same").length;

  const copySetup = async () => {
    try {
      await navigator.clipboard.writeText(analysis.setup.new_text);
    } catch {
      /* clipboard may be blocked; the download button still works */
    }
  };

  const downloadSetup = () => {
    const blob = new Blob([analysis.setup.new_text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${name.trim() || `ENG_${analysis.setup.name}`}.ini`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const parseBest = (text: string): number | null => {
    const cleaned = text.trim().replace(",", ".");
    if (!cleaned) return null;
    if (cleaned.includes(":")) {
      const [min, sec] = cleaned.split(":");
      const value = Number(min) * 60 + Number(sec);
      return Number.isFinite(value) ? Math.round(value * 1000) : null;
    }
    const value = Number(cleaned);
    return Number.isFinite(value) ? Math.round(value * 1000) : null;
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <section className="diag-banner">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <div className="card-title" style={{ fontSize: 17 }}>
              {analysis.car.name}
              <span className="muted" style={{ fontWeight: 400 }}> · {analysis.track.name}</span>
            </div>
            <div className="card-sub">
              Setup {analysis.setup.name} · {analysis.changes.length} cambio(s) propuesto(s) ·{" "}
              {analysis.llm_used ? "redactado con Ollama" : "plantilla determinística"}
            </div>
          </div>
          <div className="row">
            <button className="btn small ghost" onClick={copySetup}>
              Copiar .ini
            </button>
            <button className="btn small ghost" onClick={downloadSetup}>
              Descargar
            </button>
          </div>
        </div>

        <div className="issue-list">
          {analysis.diagnosis.issues.map((issue) => (
            <span className="chip bad" key={`${issue.type}-${issue.phase}-${issue.speed}`}>
              {issue.label} · {issue.source}
            </span>
          ))}
          {analysis.diagnosis.issues.length === 0 ? (
            <span className="chip warn">Sin síntomas específicos</span>
          ) : null}
        </div>

        {analysis.diagnosis.missing.length > 0 ? (
          <div className="callout" style={{ marginTop: 12 }}>
            <strong>Datos faltantes:</strong> {analysis.diagnosis.missing.join(" ")}
          </div>
        ) : null}
      </section>

      <div className="grid side">
        <div>
          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Plan de cambios</div>
                <div className="card-sub">Aplicá el paquete completo y validá en pista.</div>
              </div>
            </div>

            {analysis.changes.length === 0 ? (
              <div className="empty">
                No hay cambios numéricos seguros para proponer con los datos actuales. Cargá temperaturas,
                presiones y una descripción por fase.
              </div>
            ) : (
              analysis.changes.map((change) => <ChangeCard change={change} key={`${change.role}-${change.rules.join()}`} />)
            )}

            {analysis.diagnosis.conflicts.length > 0 ? (
              <div style={{ marginTop: 12 }}>
                {analysis.diagnosis.conflicts.map((conflict) => (
                  <div className="callout warn" key={conflict}>
                    {conflict}
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Cómo probarlo</div>
                <div className="card-sub">{analysis.test_plan.conditions}</div>
              </div>
            </div>
            <ol className="plan-list">
              {analysis.test_plan.procedure.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <div className="section-label" style={{ marginTop: 16 }}>
              Qué mirar
            </div>
            <ul className="plan-list">
              {analysis.test_plan.watch.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div className="callout ok" style={{ marginTop: 14 }}>
              <strong>Criterio de éxito:</strong> {analysis.test_plan.success_criteria}
            </div>
            {analysis.test_plan.test_laps ? (
              <div className="muted small" style={{ marginTop: 8 }}>
                Objetivo: {analysis.test_plan.test_laps} vueltas cronometradas tras 1 de calentamiento.
              </div>
            ) : null}
          </section>
        </div>

        <div>
          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Explicación del ingeniero</div>
              </div>
              {props.llmReady && !analysis.llm_used ? (
                <button className="btn small ghost" onClick={props.onNarrate} disabled={props.narrating}>
                  {props.narrating ? "Redactando…" : "Redactar con Ollama"}
                </button>
              ) : null}
            </div>
            <div className="explanation">{analysis.explanation}</div>
            {analysis.llm_error ? (
              <div className="callout warn" style={{ marginTop: 10 }}>
                Ollama falló: {analysis.llm_error}. Se muestra la explicación determinística.
              </div>
            ) : null}
          </section>

          {analysis.warnings.length > 0 ? (
            <section className="card">
              <div className="card-head">
                <div className="card-title">Avisos</div>
              </div>
              {analysis.warnings.map((warning) => (
                <div className="callout warn" key={warning}>
                  {warning}
                </div>
              ))}
            </section>
          ) : null}

          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Guardar como setup nuevo</div>
                <div className="card-sub">
                  Tu archivo original no se toca. Se escribe un .ini nuevo en la misma carpeta.
                </div>
              </div>
            </div>

            {props.savedPath ? (
              <div className="callout ok">
                Guardado en <span className="mono">{props.savedPath}</span>
                <div style={{ marginTop: 8 }}>
                  Cargalo desde boxes en Assetto Corsa (los setups no se recargan en caliente).
                </div>
              </div>
            ) : (
              <>
                <div className="field">
                  <label>Nombre del archivo</label>
                  <input
                    className="input"
                    placeholder={`ENG_${analysis.setup.name}`}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </div>
                <div className="row" style={{ marginTop: 12 }}>
                  <button className="btn primary" onClick={() => props.onSave(name)} disabled={props.saving}>
                    {props.saving ? "Guardando…" : "Guardar .ini"}
                  </button>
                  <span className="muted small">Si el nombre existe, se agrega un sufijo.</span>
                </div>
              </>
            )}

            {props.savedPath ? (
              <div style={{ marginTop: 18, borderTop: "1px solid var(--border-soft)", paddingTop: 16 }}>
                <div className="section-label">Registrar resultado del test</div>
                {props.resultSaved ? (
                  <div className="callout ok">Resultado registrado. Queda en el historial.</div>
                ) : (
                  <>
                    <div className="seg" style={{ marginBottom: 10 }}>
                      {(
                        [
                          ["better", "Mejor"],
                          ["same", "Igual"],
                          ["worse", "Peor"],
                          ["unknown", "Sin datos"],
                        ] as const
                      ).map(([key, label]) => (
                        <button key={key} className={outcome === key ? "on" : ""} onClick={() => setOutcome(key)}>
                          {label}
                        </button>
                      ))}
                    </div>
                    <div className="grid two">
                      <div className="field">
                        <label>Mejor vuelta</label>
                        <input
                          className="input"
                          placeholder="2:13.900"
                          value={bestLap}
                          onChange={(event) => setBestLap(event.target.value)}
                        />
                      </div>
                      <div className="field">
                        <label>Notas</label>
                        <input
                          className="input"
                          placeholder="El subviraje mejoró; quedó nervioso en la 12."
                          value={resultNotes}
                          onChange={(event) => setResultNotes(event.target.value)}
                        />
                      </div>
                    </div>
                    <div className="row" style={{ marginTop: 10 }}>
                      <button
                        className="btn"
                        onClick={() => props.onResult(outcome, resultNotes, parseBest(bestLap))}
                      >
                        Guardar resultado
                      </button>
                    </div>
                  </>
                )}
              </div>
            ) : null}
          </section>

          <section className="card">
            <div className="card-head">
              <div>
                <div className="card-title">Diff del archivo</div>
                <div className="card-sub">{changed} línea(s) modificada(s) de {diff.length}.</div>
              </div>
            </div>
            <div className="diff">
              {diff.map((line, index) => (
                <div className={`diff-line ${line.type}`} key={`${index}-${line.text}`}>
                  <span className="ln">{index + 1}</span>
                  <span>
                    {line.type === "add" ? "+ " : line.type === "del" ? "- " : "  "}
                    {line.text}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <div className="row end">
            {props.sessionId ? (
              <button className="btn primary" onClick={props.onContinueSession}>
                Continuar sesión →
              </button>
            ) : null}
            <button className="btn ghost" onClick={props.onBack}>
              ← Ajustar sensaciones
            </button>
          </div>
        </div>
      </div>

      {analysis.analysis_id ? (
        <div className="muted small center">
          Análisis #{analysis.analysis_id} · {new Date(analysis.created_at).toLocaleString("es-AR")}
        </div>
      ) : null}
    </div>
  );
}
