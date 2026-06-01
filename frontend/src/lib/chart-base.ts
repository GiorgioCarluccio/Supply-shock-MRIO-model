/**
 * Shared ECharts styling helpers that encode the OpenEconomics dataviz rules:
 * white canvas, no border, horizontal gridlines on the value axis only,
 * Atkinson fonts, grey reference tones.
 */
import { BRAND, GRIDLINE_GREY } from "@/lib/brand";

export const FONT_SANS =
  "var(--font-atkinson), Inter, system-ui, sans-serif";
export const FONT_MONO = "var(--font-mono), ui-monospace, monospace";

export const textStyle = { fontFamily: FONT_SANS, color: BRAND.black };

export const baseTooltip = {
  trigger: "item" as const,
  backgroundColor: BRAND.white,
  borderColor: BRAND.greyMid,
  borderWidth: 1,
  textStyle: { color: BRAND.black, fontFamily: FONT_SANS, fontSize: 12 },
  extraCssText: "box-shadow:0 2px 8px rgba(0,0,0,0.08);border-radius:4px;",
};

/** Axis label style (mono, grey). */
export const axisLabel = {
  fontFamily: FONT_MONO,
  fontSize: 11,
  color: BRAND.greyText,
};

/** Value axis with horizontal gridlines (grey, 0.5pt-equivalent). */
export function valueAxis(name?: string) {
  return {
    type: "value" as const,
    name,
    nameTextStyle: { fontFamily: FONT_SANS, color: BRAND.greyText, fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: GRIDLINE_GREY, width: 1 } },
    axisLabel,
  };
}

/** Category axis, no gridlines. */
export function categoryAxis(data: string[], inverse = false) {
  return {
    type: "category" as const,
    data,
    inverse,
    axisLine: { lineStyle: { color: GRIDLINE_GREY } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { ...axisLabel, fontFamily: FONT_SANS },
  };
}

export const chartGrid = {
  left: 8,
  right: 24,
  top: 16,
  bottom: 8,
  containLabel: true,
};
