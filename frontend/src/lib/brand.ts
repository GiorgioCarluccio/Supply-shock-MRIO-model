/**
 * OpenEconomics brand tokens and data-visualisation rules.
 * Centralised so charts and components never hardcode hex values inline.
 *
 * Source: OpenEconomics brand manual + openeconomics-brand-dataviz skill.
 */

export const BRAND = {
  white: "#FFFFFF",
  black: "#000000",
  bluette: "#4400B3", // BLUETTE_700 — primary accent
  bluette500: "#6E1AFF", // violet
  bluette400: "#8B5CFF",
  bluette900: "#2B0073",
  lime: "#B9FF69", // secondary accent — positive emphasis / active state
  magenta: "#C300C3",
  cyan: "#00FFFF",
  yellow: "#FFF300",
  greyText: "#595959",
  greyMid: "#DDDDDA",
  greyLight: "#F4F4F2",
} as const;

/**
 * Fixed chart series colour order (brand dataviz rule).
 * Use Bluette first, Lime second (white canvas only), then violet/magenta/cyan.
 * Do not exceed 5 series without splitting the chart.
 */
export const CHART_SERIES_COLORS = [
  BRAND.bluette,
  BRAND.lime,
  BRAND.bluette500,
  BRAND.magenta,
  BRAND.cyan,
] as const;

/** Grey is reserved for baselines / reference elements only. */
export const REFERENCE_GREY = BRAND.greyText;
export const GRIDLINE_GREY = BRAND.greyMid;

/** Loss (penalised) tones — Bluette/dark. Favoured tones — Lime/positive. */
export const LOSS_COLOR = BRAND.bluette;
export const DIRECT_LOSS_COLOR = BRAND.bluette900;
export const INDIRECT_LOSS_COLOR = BRAND.bluette500;
export const FAVORED_COLOR = "#7BBF3F"; // legible lime-derived green for text/areas
export const PENALIZED_COLOR = BRAND.bluette;

/** Sequential ramp for choropleth maps (white -> bluette). */
export const MAP_RAMP = [
  "#FFFFFF",
  "#E7DCFA",
  "#C9B0F2",
  "#A77FE8",
  "#7E45D6",
  "#4400B3",
] as const;

/** Diverging ramp for flow heatmaps (favoured/lime -> neutral -> penalised/bluette). */
export const DIVERGING_RAMP = {
  positive: "#7BBF3F",
  neutral: BRAND.greyLight,
  negative: BRAND.bluette,
} as const;
