import type {
  AnalyzeResponse,
  Catalog,
  ContextPayload,
  FeedbackPayload,
  Health,
  InspectResponse,
  LlmStatus,
  AnalysisListItem,
  SessionSummary,
  SessionDetail,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),
  catalog: (force = false) => request<Catalog>(`/catalog?force=${force}`),
  refreshCatalog: () => request<Catalog>("/catalog/refresh", { method: "POST" }),
  profile: (carId: string, setupPath?: string) =>
    request<InspectResponse["profile"]>(
      `/cars/${encodeURIComponent(carId)}/profile${setupPath ? `?setup_path=${encodeURIComponent(setupPath)}` : ""}`,
    ),
  setup: (path: string) => request<InspectResponse>(`/setup?path=${encodeURIComponent(path)}`),
  inspect: (payload: { text: string; car_id?: string | null; track_id?: string | null; name?: string | null }) =>
    request<InspectResponse>("/setup/inspect", { method: "POST", body: JSON.stringify(payload) }),
  analyze: (payload: {
    setup_path?: string | null;
    setup_text?: string | null;
    setup_name?: string | null;
    car_id?: string | null;
    track_id?: string | null;
    session_id?: number | null;
    context: ContextPayload;
    feedback: FeedbackPayload;
    use_llm: boolean;
  }) => request<AnalyzeResponse>("/analyze", { method: "POST", body: JSON.stringify(payload) }),
  save: (payload: { analysis_id: number; name?: string | null; overwrite?: boolean }) =>
    request<{ path: string; name: string; already_saved: boolean }>("/save", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveResult: (payload: {
    analysis_id: number;
    best_lap_ms?: number | null;
    avg_lap_ms?: number | null;
    notes?: string;
    outcome: "better" | "same" | "worse" | "unknown";
  }) => request<{ ok: boolean }>("/result", { method: "POST", body: JSON.stringify(payload) }),
  history: (limit = 50) => request<{ analyses: AnalysisListItem[] }>(`/history?limit=${limit}`),
  sessions: (limit = 50) => request<{ sessions: SessionSummary[] }>(`/sessions?limit=${limit}`),
  session: (id: number) => request<SessionDetail>(`/sessions/${id}`),
  createSession: (payload: {
    car_id: string;
    track_id?: string | null;
    name?: string | null;
    base_setup_path?: string | null;
    notes?: string;
  }) => request<SessionDetail>("/sessions", { method: "POST", body: JSON.stringify(payload) }),
  updateSession: (id: number, payload: { name?: string | null; current_setup_path?: string | null; status?: string | null; notes?: string | null }) =>
    request<SessionDetail>(`/sessions/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  acLive: () => request<Record<string, unknown>>("/ac/live"),
  analysis: (id: number) => request<AnalyzeResponse>(`/analysis/${id}`),
  llmStatus: () => request<LlmStatus>("/llm/status"),
  narrate: (analysisId: number) =>
    request<{ explanation: string }>("/llm/narrate", {
      method: "POST",
      body: JSON.stringify({ analysis_id: analysisId }),
    }),
};
