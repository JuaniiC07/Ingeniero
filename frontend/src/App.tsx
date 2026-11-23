import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import { ContextStep } from "./components/ContextStep";
import { DiagnosisStep } from "./components/DiagnosisStep";
import { FeedbackStep } from "./components/FeedbackStep";
import { HistoryPanel } from "./components/HistoryPanel";
import { SessionPanel } from "./components/SessionPanel";
import { SetupStep } from "./components/SetupStep";
import { LiveSessionView } from "./components/LiveSessionView";
import type {
  AnalyzeResponse,
  Catalog,
  ContextPayload,
  FeedbackPayload,
  Health,
  InspectResponse,
  SessionDetail,
  SessionSummary,
} from "./types";

const STEP_LABELS = ["Setup", "Contexto", "Sensaciones", "Diagnóstico"];

const DEFAULT_CONTEXT: ContextPayload = {
  condition: "dry",
  track_type: null,
  air_temp_c: null,
  track_temp_c: null,
  grip: null,
  session_type: "practice",
  laps_target: 4,
  fuel_l: null,
  compound: null,
};

const DEFAULT_FEEDBACK: FeedbackPayload = {
  symptoms: [],
  notes: "",
  best_lap_ms: null,
  avg_lap_ms: null,
  laps_completed: null,
  tyre_temps: null,
  hot_pressures: null,
};

type View = "dev" | "live";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);

  const [view, setView] = useState<View>("dev");
  const [step, setStep] = useState(0);
  const [carId, setCarId] = useState<string | null>(null);
  const [trackId, setTrackId] = useState<string | null>(null);
  const [setupPath, setSetupPath] = useState<string | null>(null);
  const [mode, setMode] = useState<"saved" | "paste">("saved");
  const [customText, setCustomText] = useState("");
  const [inspect, setInspect] = useState<InspectResponse | null>(null);

  const [context, setContext] = useState<ContextPayload>(DEFAULT_CONTEXT);
  const [feedback, setFeedback] = useState<FeedbackPayload>(DEFAULT_FEEDBACK);
  const [useLlm, setUseLlm] = useState(false);

  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [savedPath, setSavedPath] = useState<string | null>(null);
  const [resultSaved, setResultSaved] = useState(false);
  const [narrating, setNarrating] = useState(false);

  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<unknown[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [session, setSession] = useState<SessionDetail | null>(null);

  const [acLiveLoading, setAcLiveLoading] = useState(false);

  const [toast, setToast] = useState<{ kind: "ok" | "bad"; text: string } | null>(null);

  const llmReady = Boolean(health?.llm.ready);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [healthData, catalogData] = await Promise.all([api.health(), api.catalog()]);
        if (!alive) return;
        setHealth(healthData);
        setCatalog(catalogData);
      } catch (err) {
        if (alive) setBootError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const invalidateAnalysis = useCallback(() => {
    setAnalysis(null);
    setSavedPath(null);
    setResultSaved(false);
  }, []);

  const handleCar = useCallback(
    (id: string) => {
      setCarId(id);
      setSetupPath(null);
      setInspect(null);
      setError(null);
      invalidateAnalysis();
    },
    [invalidateAnalysis],
  );

  const handleTrack = useCallback(
    (id: string) => {
      setTrackId(id || null);
      invalidateAnalysis();
    },
    [invalidateAnalysis],
  );

  const handleSetup = useCallback(
    async (path: string) => {
      setBusy(true);
      setError(null);
      setSetupPath(path);
      invalidateAnalysis();
      try {
        const data = await api.setup(path);
        setInspect(data);
        setCarId(data.car.car_id);
        if (data.track.track_id && data.track.track_id !== "generic") setTrackId(data.track.track_id);
        setContext((prev) => ({ ...prev, track_type: prev.track_type ?? data.track.type }));
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setInspect(null);
      } finally {
        setBusy(false);
      }
    },
    [invalidateAnalysis],
  );

  const handleInspectText = useCallback(async () => {
    setBusy(true);
    setError(null);
    invalidateAnalysis();
    try {
      const data = await api.inspect({
        text: customText,
        car_id: carId,
        track_id: trackId,
      });
      setInspect(data);
      setSetupPath(null);
      setCarId(data.car.car_id);
      if (data.track.track_id && data.track.track_id !== "generic") setTrackId(data.track.track_id);
      setContext((prev) => ({ ...prev, track_type: prev.track_type ?? data.track.type }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setInspect(null);
    } finally {
      setBusy(false);
    }
  }, [customText, carId, trackId, invalidateAnalysis]);

  const handleRefreshCatalog = useCallback(async () => {
    setBusy(true);
    try {
      const data = await api.catalog(true);
      setCatalog(data);
      setToast({ kind: "ok", text: `Catálogo actualizado: ${data.counts.cars} coches, ${data.counts.setups} setups.` });
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!inspect) return;
    setBusy(true);
    setError(null);
    setSavedPath(null);
    setResultSaved(false);
    try {
      const payload: Parameters<typeof api.analyze>[0] = {
        car_id: inspect.car.car_id,
        track_id: inspect.track.track_id === "generic" ? null : inspect.track.track_id,
        setup_name: inspect.setup.name,
        session_id: sessionId,
        context: { ...context, track_type: context.track_type ?? inspect.track.type },
        feedback,
        use_llm: useLlm && llmReady,
      };
      if (setupPath && mode === "saved") {
        payload.setup_path = setupPath;
      } else {
        payload.setup_text = inspect.setup.text;
      }
      const data = await api.analyze(payload);
      setAnalysis(data);
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [inspect, setupPath, mode, context, feedback, useLlm, llmReady, sessionId]);

  const handleSave = useCallback(
    async (name: string) => {
      if (!analysis) return;
      setSaving(true);
      try {
        const result = await api.save({ analysis_id: analysis.analysis_id, name: name || null });
        setSavedPath(result.path);
        setToast({ kind: "ok", text: `Setup guardado: ${result.path}` });
      } catch (err) {
        setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
      } finally {
        setSaving(false);
      }
    },
    [analysis],
  );

  const handleResult = useCallback(
    async (outcome: "better" | "same" | "worse" | "unknown", notes: string, bestLapMs: number | null) => {
      if (!analysis) return;
      try {
        await api.saveResult({
          analysis_id: analysis.analysis_id,
          outcome,
          notes,
          best_lap_ms: bestLapMs,
        });
        setResultSaved(true);
        setToast({ kind: "ok", text: "Resultado registrado en el historial." });
      } catch (err) {
        setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
      }
    },
    [analysis],
  );

  const handleNarrate = useCallback(async () => {
    if (!analysis) return;
    setNarrating(true);
    try {
      const result = await api.narrate(analysis.analysis_id);
      setAnalysis({ ...analysis, explanation: result.explanation, llm_used: true });
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setNarrating(false);
    }
  }, [analysis]);

  const openHistory = useCallback(async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    try {
      const data = await api.history(60);
      setHistoryItems(data.analyses);
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const openAnalysis = useCallback(async (id: number) => {
    setBusy(true);
    try {
      const data = await api.analysis(id);
      setAnalysis(data);
      setSavedPath(data.saved_path ?? null);
      setResultSaved(Boolean(data.result));
      if (data.session_id) setSessionId(data.session_id);
      setStep(3);
      setHistoryOpen(false);
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await api.sessions(60);
      setSessions(data.sessions);
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const openSessions = useCallback(() => {
    setSessionsOpen(true);
    void loadSessions();
  }, [loadSessions]);

  const openSession = useCallback(
    async (id: number) => {
      setBusy(true);
      try {
        const data = await api.session(id);
        setSession(data);
        setSessionId(data.id);
        setCarId(data.car_id);
        setTrackId(data.track_id);
        const path = data.current_setup_path || data.base_setup_path;
        if (path) {
          await handleSetup(path);
        }
        setSessionsOpen(false);
        setToast({ kind: "ok", text: `Sesión #${data.id} cargada.` });
      } catch (err) {
        setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
      } finally {
        setBusy(false);
      }
    },
    [handleSetup],
  );

  const createSessionFromCurrent = useCallback(async () => {
    if (!inspect) {
      setToast({ kind: "bad", text: "Cargá un setup primero." });
      return;
    }
    setBusy(true);
    try {
      const data = await api.createSession({
        car_id: inspect.car.car_id,
        track_id: inspect.track.track_id === "generic" ? null : inspect.track.track_id,
        name: `${inspect.car.name} · ${inspect.track.name}`,
        base_setup_path: setupPath,
      });
      setSession(data);
      setSessionId(data.id);
      setToast({ kind: "ok", text: `Sesión #${data.id} creada. Los ajustes quedarán encadenados.` });
      void loadSessions();
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }, [inspect, setupPath, loadSessions]);

  const continueSession = useCallback(async () => {
    if (!session) return;
    const path = savedPath || session.current_setup_path || session.base_setup_path;
    if (!path) {
      setToast({ kind: "bad", text: "No hay setup base para continuar." });
      return;
    }
    setBusy(true);
    try {
      await handleSetup(path);
      setContext((prev) => ({ ...prev }));
      setFeedback(DEFAULT_FEEDBACK);
      setStep(2);
      setToast({ kind: "ok", text: "Seguí con el feedback del nuevo test." });
    } catch (err) {
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }, [session, savedPath, handleSetup]);

  const handleAcLive = useCallback(async () => {
    setAcLiveLoading(true);
    try {
      const data = (await api.acLive()) as Record<string, unknown>;
      if (!data.available) {
        setToast({ kind: "bad", text: "Assetto Corsa no está corriendo o no hay sesión activa." });
        return;
      }
      if (data.status !== "live") {
        setToast({ kind: "bad", text: `AC está en estado "${data.status}". Entrá a pista para leer datos.` });
      }
      const liveCar = typeof data.car_id === "string" ? data.car_id : null;
      const liveTrack = typeof data.track_id === "string" ? data.track_id : null;
      if (liveCar && catalog?.cars.some((c) => c.car_id === liveCar)) {
        setCarId(liveCar);
      }
      if (liveTrack && catalog?.tracks.some((t) => t.track_id === liveTrack)) {
        setTrackId(liveTrack);
      }
      setContext((prev) => ({
        ...prev,
        air_temp_c: typeof data.air_temp_c === "number" ? (data.air_temp_c as number) : prev.air_temp_c,
        track_temp_c: typeof data.road_temp_c === "number" ? (data.road_temp_c as number) : prev.track_temp_c,
        fuel_l: typeof data.fuel_l === "number" ? (data.fuel_l as number) : prev.fuel_l,
        compound: typeof data.tyre_compound === "string" ? (data.tyre_compound as string) : prev.compound,
        grip: typeof data.surface_grip === "number" ? Math.round((data.surface_grip as number) * 100) : prev.grip,
        session_type:
          data.session_type === "qualifying" || data.session_type === "race" || data.session_type === "test"
            ? (data.session_type as ContextPayload["session_type"])
            : prev.session_type,
      }));
      const temps = data.tyre_temps as Record<string, { inner?: number; middle?: number; outer?: number }> | undefined;
      const pressures = data.tyre_pressures as Record<string, number> | undefined;
      setFeedback((prev) => ({
        ...prev,
        tyre_temps: temps
          ? {
              lf: { inner: temps.lf?.inner ?? null, middle: temps.lf?.middle ?? null, outer: temps.lf?.outer ?? null },
              rf: { inner: temps.rf?.inner ?? null, middle: temps.rf?.middle ?? null, outer: temps.rf?.outer ?? null },
              lr: { inner: temps.lr?.inner ?? null, middle: temps.lr?.middle ?? null, outer: temps.lr?.outer ?? null },
              rr: { inner: temps.rr?.inner ?? null, middle: temps.rr?.middle ?? null, outer: temps.rr?.outer ?? null },
            }
          : prev.tyre_temps,
        hot_pressures: pressures ? { ...pressures } : prev.hot_pressures,
        best_lap_ms: typeof data.best_lap_ms === "number" ? (data.best_lap_ms as number) : prev.best_lap_ms,
        laps_completed: typeof data.completed_laps === "number" ? (data.completed_laps as number) : prev.laps_completed,
      }));
      if (!inspect && liveCar && catalog) {
        const setups = catalog.setups.filter((s) => s.car_id === liveCar && (liveTrack ? s.track_id === liveTrack : true));
        if (setups.length) {
          const latest = setups.sort((a, b) => b.modified.localeCompare(a.modified))[0];
          await handleSetup(latest.path);
        }
      }
      setToast({ kind: "ok", text: `Leído de AC: ${liveCar ?? "?"} en ${liveTrack ?? "?"}.` });
    } catch (err) {
      console.error("AC live error:", err);
      setToast({ kind: "bad", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setAcLiveLoading(false);
    }
  }, [catalog, inspect, handleSetup]);

  const canGo = useMemo(
    () => [true, Boolean(inspect), Boolean(inspect), Boolean(analysis)],
    [inspect, analysis],
  );

  if (bootError) {
    return (
      <div className="app-shell">
        <div className="main">
          <div className="card">
            <div className="card-title">No pude iniciar Ingeniero</div>
            <div className="callout bad" style={{ marginTop: 12 }}>
              {bootError}
            </div>
            <div className="callout" style={{ marginTop: 10 }}>
              Asegurate de que el backend esté corriendo en <span className="mono">http://127.0.0.1:8000</span> y
              que Assetto Corsa esté instalado (o definí <span className="mono">AC_INSTALL</span>).
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!catalog || !health) {
    return (
      <div className="app-shell">
        <div className="loading-bar" />
        <div className="main">
          <div className="empty">Escaneando Assetto Corsa…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {busy || acLiveLoading ? <div className="loading-bar" /> : null}

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">IN</div>
          <div className="brand-text">
            <strong>Ingeniero</strong>
            <span>Ingeniero de pista para Assetto Corsa</span>
          </div>
        </div>
        <div className="topbar-spacer" />
        <nav className="seg" style={{ marginRight: 12 }}>
          <button className={view === "dev" ? "on" : ""} onClick={() => setView("dev")}>
            Desarrollo
          </button>
          <button className={view === "live" ? "on" : ""} onClick={() => setView("live")}>
            Sesión en vivo
          </button>
        </nav>
        <div className="status-cluster">
          <button className="btn small" onClick={handleAcLive} disabled={acLiveLoading}>
            {acLiveLoading ? "Leyendo AC…" : "📡 Leer de AC"}
          </button>
          {sessionId ? <span className="chip ok">Sesión #{sessionId}</span> : null}
          <span className="status-pill ok">
            <span className="status-dot" />
            AC · {catalog.counts.cars} coches
          </span>
          <span className={`status-pill ${health.llm.ready ? "ok" : "warn"}`}>
            <span className="status-dot" />
            {health.llm.ready ? `Ollama · ${health.llm.model}` : "Ollama no detectado"}
          </span>
          <button className="btn small ghost" onClick={openSessions}>
            Sesiones
          </button>
          <button className="btn small ghost" onClick={openHistory}>
            Historial
          </button>
        </div>
      </header>

      <main className="main">
        {view === "live" ? (
          <LiveSessionView inspect={inspect} onUseData={handleAcLive} />
        ) : (
          <>
            <nav className="stepper">
              {STEP_LABELS.map((label, index) => {
                const disabled = index > 0 && !canGo[index];
                return (
                  <button
                    key={label}
                    className={`step ${step === index ? "active" : ""} ${index < step ? "done" : ""}`}
                    disabled={disabled}
                    onClick={() => setStep(index)}
                  >
                    <span className="step-index">{index < step ? "✓" : index + 1}</span>
                    {label}
                  </button>
                );
              })}
            </nav>

            {step === 0 ? (
              <SetupStep
                catalog={catalog}
                carId={carId}
                trackId={trackId}
                setupPath={setupPath}
                inspect={inspect}
                mode={mode}
                customText={customText}
                busy={busy}
                error={error}
                sessionId={sessionId}
                onCar={handleCar}
                onTrack={handleTrack}
                onSetup={handleSetup}
                onMode={setMode}
                onCustomText={setCustomText}
                onInspectText={handleInspectText}
                onRefresh={handleRefreshCatalog}
                onNext={() => setStep(1)}
                onCreateSession={createSessionFromCurrent}
              />
            ) : null}

            {step === 1 && inspect ? (
              <ContextStep
                inspect={inspect}
                context={context}
                onChange={(patch) => setContext((prev) => ({ ...prev, ...patch }))}
                onBack={() => setStep(0)}
                onNext={() => setStep(2)}
              />
            ) : null}

            {step === 2 && inspect ? (
              <FeedbackStep
                feedback={feedback}
                onChange={(patch) => setFeedback((prev) => ({ ...prev, ...patch }))}
                onBack={() => setStep(1)}
                onAnalyze={handleAnalyze}
                busy={busy}
                error={error}
                useLlm={useLlm}
                setUseLlm={setUseLlm}
                llmReady={llmReady}
                llmModel={health.llm.model}
              />
            ) : null}

            {step === 3 && analysis ? (
              <DiagnosisStep
                analysis={analysis}
                onBack={() => setStep(2)}
                onSave={handleSave}
                saving={saving}
                savedPath={savedPath}
                onResult={handleResult}
                resultSaved={resultSaved}
                onNarrate={handleNarrate}
                narrating={narrating}
                llmReady={llmReady}
                sessionId={sessionId}
                onContinueSession={continueSession}
              />
            ) : null}

            {step === 3 && !analysis ? (
              <div className="empty">Generá un diagnóstico primero.</div>
            ) : null}
          </>
        )}
      </main>

      <HistoryPanel
        open={historyOpen}
        loading={historyLoading}
        items={historyItems as never}
        onClose={() => setHistoryOpen(false)}
        onOpen={openAnalysis}
      />

      <SessionPanel
        open={sessionsOpen}
        loading={sessionsLoading}
        items={sessions}
        onClose={() => setSessionsOpen(false)}
        onOpen={openSession}
        onCreate={() => {
          setSessionsOpen(false);
          createSessionFromCurrent();
        }}
      />

      {toast ? <div className={`toast ${toast.kind}`}>{toast.text}</div> : null}
    </div>
  );
}
