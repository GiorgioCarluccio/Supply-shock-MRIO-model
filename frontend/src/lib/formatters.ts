/**
 * Number formatting helpers. The model output values are expressed in the
 * SAM's native monetary unit (millions of EUR by construction of the IO table);
 * we label them as "M€" and keep formatting consistent across the dashboard.
 *
 * Uses a proper minus sign for negatives, per brand dataviz rules.
 */

const MINUS = "−";

function withSign(formatted: string, value: number): string {
  if (value < 0) return `${MINUS}${formatted}`;
  return formatted;
}

/** Monetary value in the model unit (M€). Compact for large numbers. */
export function fmtMoney(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
  const abs = Math.abs(value);
  let out: string;
  if (abs >= 1_000_000) out = `${(abs / 1_000_000).toFixed(digits)}T€`;
  else if (abs >= 1_000) out = `${(abs / 1_000).toFixed(digits)}B€`;
  else out = `${abs.toFixed(digits)}M€`;
  return withSign(out, value);
}

/** Plain number with thousands separators. */
export function fmtNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
  const formatted = Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return withSign(formatted, value);
}

/** Percentage from a 0–1 ratio. */
export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
  const out = `${(Math.abs(value) * 100).toFixed(digits)}%`;
  return withSign(out, value);
}

/** Percentage from an already-percentage number. */
export function fmtPctRaw(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
  return `${value.toFixed(digits)}%`;
}

/** Small ratios shown with more precision (e.g. mean supply shock). */
export function fmtShock(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
  return fmtPct(value, 2);
}

export function fmtDays(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
  return `${value.toFixed(digits)} d`;
}
