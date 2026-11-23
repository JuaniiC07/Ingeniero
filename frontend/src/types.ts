export interface CarSummary {
  car_id: string;
  name: string;
  brand: string;
  class: string;
  car_class: string;
  tags: string[];
  has_data_folder: boolean;
  has_data_acd: boolean;
  has_profile: boolean;
  saved_setups: number;
}

export interface TrackInfo {
  track_id: string;
  name: string;
  length_m: number | null;
  tags: string[];
  country: string;
  city: string;
  run: string;
  type: string;
  type_label: string;
  pitboxes?: number | null;
}

export interface SetupSummary {
  id: string;
  car_id: string;
  track_id: string;
  name: string;
  file_name: string;
  path: string;
  modified: string;
  size: number;
  generated: boolean;
  lap_ms: number | null;
}

export interface Catalog {
  generated_at: string;
  ac_install: string;
  documents: string;
  cars: CarSummary[];
  tracks: TrackInfo[];
  setups: SetupSummary[];
  counts: { cars: number; tracks: number; setups: number };
}

export interface ParamInfo {
  section: string;
  label: string;
  tab: string;
  unit: string;
  mode: string;
  display: number;
  current: number;
  minimum: number;
  maximum: number;
  min_display: number;
  max_display: number;
  step_display: number;
  step: number;
  decimals: number;
  has_value: boolean;
  show_clicks: number;
  note: string;
  help: string;
}

export interface CarProfile {
  car_id: string;
  name: string;
  brand: string;
  car_class: string;
  tags: string[];
  spec_source: string;
  spec_available: boolean;
  saved_setups: number;
  warnings: string[];
  params: ParamInfo[];
  groups: Record<string, ParamInfo[]>;
}

export interface InspectResponse {
  setup: {
    name: string;
    path: string | null;
    text: string;
    values: Record<string, string>;
  };
  car: CarSummary;
  track: TrackInfo;
  profile: CarProfile;
  warnings: string[];
}

export type SymptomType =
  | "understeer"
  | "oversteer"
  | "wheelspin"
  | "lockup_front"
  | "lockup_rear"
  | "braking_instability"
  | "bottoming"
  | "kerb"
  | "tyre_inner_hot_front"
  | "tyre_inner_hot_rear"
  | "tyre_outer_hot_front"
  | "tyre_outer_hot_rear"
  | "tyre_center_hot"
  | "top_speed"
  | "low_grip";

export type Phase = "entry" | "mid" | "exit" | "braking" | "straight" | "any";
export type Speed = "slow" | "medium" | "fast" | "any";

export interface Symptom {
  type: SymptomType;
  phase: Phase;
  speed: Speed;
  severity: number;
}

export interface ContextPayload {
  condition: "dry" | "damp" | "wet";
  track_type: string | null;
  air_temp_c: number | null;
  track_temp_c: number | null;
  grip: number | null;
  session_type: "practice" | "qualifying" | "race" | "test";
  laps_target: number;
  fuel_l: number | null;
  compound: string | null;
}

export type TyreKey = "lf" | "rf" | "lr" | "rr";

export interface TyreTemp {
  inner: number | null;
  middle: number | null;
  outer: number | null;
}

export interface FeedbackPayload {
  symptoms: Symptom[];
  notes: string;
  best_lap_ms: number | null;
  avg_lap_ms: number | null;
  laps_completed: number | null;
  tyre_temps: Partial<Record<TyreKey, TyreTemp>> | null;
  hot_pressures: Partial<Record<TyreKey, number>> | null;
}

export interface ChangeItem {
  role: string;
  sections: string[];
  category: string;
  category_label: string;
  risk: string;
  risk_label: string;
  rules: string[];
  rule_name: string;
  reason: string;
  effect: string;
  confidence: number;
  confidence_label: string;
  before: { section: string; label: string; value: number; unit: string; file: string }[];
  after: { section: string; label: string; value: number; unit: string; file: string }[];
  delta: number;
  delta_unit: string;
  summary: string;
}

export interface Issue {
  type: string;
  label: string;
  phase: string;
  phase_label: string;
  speed: string;
  speed_label: string;
  severity: number;
  source: string;
}

export interface TestPlan {
  baseline_laps: number;
  test_laps: number;
  procedure: string[];
  watch: string[];
  success_criteria: string;
  conditions: string;
}

export interface AnalyzeResponse {
  analysis_id: number;
  created_at: string;
  car: { car_id: string; name: string; brand: string; car_class: string; tags: string[]; spec_source: string; saved_setups: number };
  track: { track_id: string; name: string; type: string };
  setup: {
    name: string;
    path: string | null;
    text: string;
    new_text: string;
    file_changes: Record<string, string>;
    profile?: CarProfile | null;
  };
  diagnosis: {
    summary: string;
    issues: Issue[];
    conflicts: string[];
    missing: string[];
  };
  changes: ChangeItem[];
  test_plan: TestPlan;
  explanation: string;
  warnings: string[];
  llm_used: boolean;
  llm_error: string | null;
  saved_path?: string | null;
  status?: string;
  result?: Record<string, unknown> | null;
  session_id?: number | null;
}

export interface AnalysisListItem {
  id: number;
  created_at: string;
  car_id: string;
  car_name: string;
  track_id: string;
  track_name: string;
  setup_name: string;
  status: string;
  saved_path: string | null;
  summary: string | null;
  changes: string[];
  result: Record<string, unknown> | null;
}

export interface SessionSummary {
  id: number;
  created_at: string;
  name: string | null;
  car_id: string;
  car_name: string;
  track_id: string;
  track_name: string;
  base_setup_path: string | null;
  current_setup_path: string | null;
  status: string;
  notes: string | null;
  analysis_count: number;
}

export interface SessionSummary {
  id: number;
  created_at: string;
  name: string | null;
  car_id: string;
  car_name: string;
  track_id: string;
  track_name: string;
  base_setup_path: string | null;
  current_setup_path: string | null;
  status: string;
  notes: string | null;
  analysis_count: number;
}

export interface SessionDetail extends SessionSummary {
  analyses: AnalyzeResponse[];
}

export interface LlmStatus {
  available: boolean;
  base_url: string;
  models: string[];
  model: string | null;
  ready: boolean;
  error?: string;
}

export interface Health {
  ok: boolean;
  ac_install: string;
  documents: string;
  llm: LlmStatus;
}
