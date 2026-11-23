import type { Phase, Speed, SymptomType } from "./types";

export interface SymptomDef {
  type: SymptomType;
  label: string;
  group: string;
  hint: string;
  phases: Phase[];
  speeds: Speed[];
}

export const PHASE_LABEL: Record<Phase, string> = {
  entry: "Entrada",
  mid: "Medio",
  exit: "Salida",
  braking: "Frenada",
  straight: "Recta",
  any: "General",
};

export const SPEED_LABEL: Record<Speed, string> = {
  slow: "Lenta",
  medium: "Media",
  fast: "Rápida",
  any: "Todas",
};

const ALL_PHASES: Phase[] = ["entry", "mid", "exit", "any"];
const ALL_SPEEDS: Speed[] = ["slow", "medium", "fast", "any"];

export const SYMPTOMS: SymptomDef[] = [
  {
    type: "understeer",
    label: "Subviraje",
    group: "Balance",
    hint: "El coche no gira lo suficiente; hay que abrir el volante.",
    phases: ALL_PHASES,
    speeds: ALL_SPEEDS,
  },
  {
    type: "oversteer",
    label: "Sobreviraje",
    group: "Balance",
    hint: "La trasera se va; hay que corregir con contravolante.",
    phases: ALL_PHASES,
    speeds: ALL_SPEEDS,
  },
  {
    type: "wheelspin",
    label: "Patina al acelerar",
    group: "Tracción",
    hint: "Las ruedas traseras giran de más a la salida.",
    phases: ["exit", "any"],
    speeds: ["slow", "medium", "fast", "any"],
  },
  {
    type: "lockup_front",
    label: "Bloqueo delantero",
    group: "Frenada",
    hint: "Las ruedas delanteras se bloquean al frenar.",
    phases: ["braking", "entry", "any"],
    speeds: ALL_SPEEDS,
  },
  {
    type: "lockup_rear",
    label: "Bloqueo trasero",
    group: "Frenada",
    hint: "La trasera se bloquea y cruza al frenar.",
    phases: ["braking", "entry", "any"],
    speeds: ALL_SPEEDS,
  },
  {
    type: "braking_instability",
    label: "Inestable al frenar",
    group: "Frenada",
    hint: "El coche se mueve o se cruza en frenada recta.",
    phases: ["braking", "entry", "any"],
    speeds: ALL_SPEEDS,
  },
  {
    type: "bottoming",
    label: "Hace tope / fondo",
    group: "Chasis",
    hint: "Golpes secos en compresiones o pianos fuertes.",
    phases: ["any"],
    speeds: ALL_SPEEDS,
  },
  {
    type: "kerb",
    label: "Mal sobre pianos",
    group: "Chasis",
    hint: "Pierde contacto o rebota al subir pianos.",
    phases: ["any"],
    speeds: ["slow", "medium", "any"],
  },
  {
    type: "tyre_inner_hot_front",
    label: "Delantera: goma caliente por dentro",
    group: "Neumáticos",
    hint: "Temperatura interior bastante mayor que la exterior.",
    phases: ["any"],
    speeds: ["any"],
  },
  {
    type: "tyre_outer_hot_front",
    label: "Delantera: goma caliente por fuera",
    group: "Neumáticos",
    hint: "Temperatura exterior bastante mayor que la interior.",
    phases: ["any"],
    speeds: ["any"],
  },
  {
    type: "tyre_inner_hot_rear",
    label: "Trasera: goma caliente por dentro",
    group: "Neumáticos",
    hint: "Temperatura interior trasera demasiado alta.",
    phases: ["any"],
    speeds: ["any"],
  },
  {
    type: "tyre_outer_hot_rear",
    label: "Trasera: goma caliente por fuera",
    group: "Neumáticos",
    hint: "Temperatura exterior trasera demasiado alta.",
    phases: ["any"],
    speeds: ["any"],
  },
  {
    type: "tyre_center_hot",
    label: "Goma caliente en el centro",
    group: "Neumáticos",
    hint: "Centro más caliente que los bordes: presión alta.",
    phases: ["any"],
    speeds: ["any"],
  },
  {
    type: "top_speed",
    label: "Falta velocidad punta",
    group: "Recta",
    hint: "El coche se queda corto al final de la recta.",
    phases: ["straight", "any"],
    speeds: ["fast", "any"],
  },
  {
    type: "low_grip",
    label: "Poco agarre general",
    group: "General",
    hint: "El coche se siente sin grip en todas las fases.",
    phases: ["any"],
    speeds: ["any"],
  },
];

export const SYMPTOM_BY_TYPE: Record<string, SymptomDef> = Object.fromEntries(
  SYMPTOMS.map((item) => [item.type, item]),
);

export const TAB_LABEL: Record<string, string> = {
  TYRES: "Neumáticos",
  ALIGNMENT: "Alineación",
  SUSPENSION: "Suspensión",
  SUSPENSIONS: "Suspensión",
  DAMPERS: "Amortiguadores",
  AERO: "Aerodinámica",
  DRIVETRAIN: "Transmisión",
  BRAKES: "Frenos",
  GENERIC: "General",
  BUMPSTOP: "Topes",
  VISUALES: "Visual",
  OTHER: "Otros",
};

export const CONDITION_LABEL = {
  dry: "Seco",
  damp: "Húmedo",
  wet: "Mojado",
} as const;

export const SESSION_LABEL = {
  practice: "Práctica",
  qualifying: "Clasificación",
  race: "Carrera",
  test: "Test",
} as const;

export const TRACK_TYPE_LABEL: Record<string, string> = {
  fast: "Rápido / alta velocidad",
  technical: "Técnico / curvas lentas",
  bumpy: "Bumpy / desniveles",
  street: "Calle / muros",
  oval: "Óvalo",
  balanced: "Mixto",
};

export function formatLap(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  const total = ms / 1000;
  const minutes = Math.floor(total / 60);
  const seconds = total - minutes * 60;
  return minutes > 0 ? `${minutes}:${seconds.toFixed(3).padStart(6, "0")}` : seconds.toFixed(3);
}

export function parseLap(text: string): number | null {
  const cleaned = text.trim().replace(",", ".");
  if (!cleaned) return null;
  if (cleaned.includes(":")) {
    const [min, sec] = cleaned.split(":");
    const minutes = Number(min);
    const seconds = Number(sec);
    if (!Number.isFinite(minutes) || !Number.isFinite(seconds)) return null;
    return Math.round((minutes * 60 + seconds) * 1000);
  }
  const seconds = Number(cleaned);
  return Number.isFinite(seconds) ? Math.round(seconds * 1000) : null;
}

export function formatNumber(value: number, decimals = 2): string {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value - Math.round(value)) < 1e-9) return String(Math.round(value));
  return value.toFixed(decimals).replace(/\.?0+$/, "");
}
