/** App-wide constants: hazards, navigation, sector labels, and data paths. */

export const APP_TITLE = "Climate Physical-Risk Impact Dashboard";
export const APP_SUBTITLE = "Provincial business-interruption impacts — Italy";

// Static data lives under <basePath>/data. The base path is injected at build
// time (NEXT_PUBLIC_BASE_PATH) so deployments under a sub-directory — e.g. a
// GitHub Pages project site at /<repo> — resolve the data files correctly.
// next/link and next/image prefix basePath automatically, but raw fetch() does
// not, so we prepend it here.
export const DATA_BASE = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/data`;

/** Core hazards and their display metadata. */
export const HAZARD_META: Record<
  string,
  { label: string; description: string }
> = {
  heatwave: {
    label: "Heatwave",
    description:
      "Derived from E-OBS maximum-temperature hot-day indicators. Single central scenario.",
  },
  flood: {
    label: "Flood",
    description:
      "Share of local business units exposed / risk-classified. Low / medium / high severity.",
  },
  landslide: {
    label: "Landslide",
    description:
      "Share of business units in PIR landslide-risk classes P1–P4 (increasing hazard).",
  },
};

export const SEVERITY_LABELS: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  central: "Central",
  p1: "P1 (moderate)",
  p2: "P2 (elevated)",
  p3: "P3 (high)",
  p4: "P4 (very high)",
};

/** Navigation sections (left sidebar / tabs). */
export const NAV_ITEMS = [
  { href: "/", label: "Overview", key: "overview" },
  { href: "/regional", label: "Regional", key: "regional" },
  { href: "/sectors", label: "Sectors", key: "sectors" },
  { href: "/network", label: "Network", key: "network" },
  { href: "/methodology", label: "Methodology", key: "methodology" },
  { href: "/data-assumptions", label: "Data & assumptions", key: "data" },
] as const;

/** NACE macro-sector (letter) human labels. */
export const MACROSECTOR_LABELS: Record<string, string> = {
  A: "Agriculture, forestry & fishing",
  B: "Mining & quarrying",
  C: "Manufacturing",
  D: "Electricity & gas",
  E: "Water & waste",
  F: "Construction",
  G: "Wholesale & retail trade",
  H: "Transport & storage",
  I: "Accommodation & food",
  J: "Information & communication",
  K: "Financial & insurance",
  L: "Real estate",
  M: "Professional & technical",
  N: "Administrative & support",
  O: "Public administration",
  P: "Education",
  Q: "Health & social work",
  R: "Arts & recreation",
  S: "Other services",
  T: "Household activities",
  U: "Extraterritorial bodies",
};

export function sectorLabel(code: string, macro?: string): string {
  const macroName = macro ? MACROSECTOR_LABELS[macro] : undefined;
  return macroName ? `${code} · ${macroName}` : code;
}

export const NO_LIVE_MODEL_NOTE =
  "The dashboard uses static precomputed scenarios; changing a selector does not run a new model.";
