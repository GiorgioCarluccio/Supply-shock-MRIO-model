/** Small colour-interpolation helpers for choropleth maps and heatmaps. */

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function rgbToHex(rgb: [number, number, number]): string {
  return (
    "#" +
    rgb
      .map((c) => Math.max(0, Math.min(255, Math.round(c))).toString(16).padStart(2, "0"))
      .join("")
  );
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

/** Interpolate within a multi-stop ramp; t in [0,1]. */
export function rampColor(stops: readonly string[], t: number): string {
  if (Number.isNaN(t)) return stops[0];
  const clamped = Math.max(0, Math.min(1, t));
  const seg = clamped * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(seg));
  const localT = seg - i;
  const a = hexToRgb(stops[i]);
  const b = hexToRgb(stops[i + 1]);
  return rgbToHex([
    lerp(a[0], b[0], localT),
    lerp(a[1], b[1], localT),
    lerp(a[2], b[2], localT),
  ]);
}

/**
 * Diverging colour for a signed value around zero.
 * Negative -> negativeColor, positive -> positiveColor, ~0 -> neutral.
 */
export function divergingColor(
  value: number,
  maxAbs: number,
  negativeColor: string,
  neutral: string,
  positiveColor: string,
): string {
  if (maxAbs <= 0) return neutral;
  const t = Math.max(-1, Math.min(1, value / maxAbs));
  if (t < 0) return rampColor([neutral, negativeColor], -t);
  return rampColor([neutral, positiveColor], t);
}

export function extent(values: number[]): [number, number] {
  let min = Infinity;
  let max = -Infinity;
  for (const v of values) {
    if (v == null || Number.isNaN(v)) continue;
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (min === Infinity) return [0, 1];
  return [min, max];
}

export function maxAbs(values: number[]): number {
  let m = 0;
  for (const v of values) {
    if (v == null || Number.isNaN(v)) continue;
    if (Math.abs(v) > m) m = Math.abs(v);
  }
  return m;
}
