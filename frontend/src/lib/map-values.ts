import type { MapValue } from "@/components/charts/ProvinceMap";
import { fmtMoney, fmtPct, fmtShock } from "@/lib/formatters";
import type { MapMetric, ProvinceMetric } from "@/lib/types";

export const MAP_METRIC_LABELS: Record<MapMetric, string> = {
  raw_exposure: "Hazard exposure",
  mean_supply_shock: "Mean supply shock",
  total_loss: "Total production loss",
  loss_rate: "Loss rate",
};

/** Build the region_code -> MapValue lookup the ProvinceMap consumes. */
export function buildMapValues(
  metrics: ProvinceMetric[],
  metric: MapMetric,
): Map<string, MapValue> {
  const map = new Map<string, MapValue>();
  for (const m of metrics) {
    const value = (m[metric] as number | null) ?? null;
    map.set(m.region_code, {
      regionCode: m.region_code,
      name: m.province_name ?? m.region_code,
      value,
      tooltip: [
        { label: "Hazard exposure", value: fmtShock(m.raw_exposure) },
        { label: "Supply shock", value: fmtShock(m.mean_supply_shock) },
        { label: "Demand shock", value: fmtShock(m.mean_demand_shock) },
        { label: "Total loss", value: fmtMoney(m.total_loss, 1) },
        { label: "Loss rate", value: fmtPct(m.loss_rate, 2) },
        { label: "Direct", value: fmtMoney(m.direct_loss, 1) },
        { label: "Indirect", value: fmtMoney(m.indirect_loss, 1) },
      ],
    });
  }
  return map;
}
