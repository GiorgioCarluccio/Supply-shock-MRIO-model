"use client";

import { FAVORED_COLOR, PENALIZED_COLOR } from "@/lib/brand";
import { fmtMoney, fmtPct } from "@/lib/formatters";
import { useRegionLabels } from "@/lib/lookups";
import type { FlowRecord } from "@/lib/types";

/**
 * Ranked table of economic flows (penalised or favoured). Shows origin and
 * destination region·sector, absolute change, and relative change.
 */
export function FlowTable({
  flows,
  mode,
  limit = 15,
}: {
  flows: FlowRecord[];
  mode: "penalized" | "favored";
  limit?: number;
}) {
  const region = useRegionLabels();
  const color = mode === "penalized" ? PENALIZED_COLOR : FAVORED_COLOR;
  const rows = [...flows]
    .sort((a, b) =>
      mode === "penalized"
        ? a.delta_value - b.delta_value
        : b.delta_value - a.delta_value,
    )
    .slice(0, limit);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-grey-mid text-left text-[11px] uppercase tracking-wide text-grey-text">
            <th className="py-2 pr-3 font-medium">Origin</th>
            <th className="py-2 pr-3 font-medium">Destination</th>
            <th className="py-2 pr-3 text-right font-medium">Δ value</th>
            <th className="py-2 text-right font-medium">Δ %</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((f, i) => (
            <tr
              key={`${f.origin_node_id}-${f.destination_node_id}-${i}`}
              className="border-b border-grey-light"
            >
              <td className="py-1.5 pr-3 text-xs" title={region.full(f.origin_region)}>
                {region.abbr(f.origin_region)}
                <span className="font-mono text-grey-text"> · {f.origin_sector}</span>
              </td>
              <td
                className="py-1.5 pr-3 text-xs"
                title={region.full(f.destination_region)}
              >
                {region.abbr(f.destination_region)}
                <span className="font-mono text-grey-text"> · {f.destination_sector}</span>
              </td>
              <td
                className="py-1.5 pr-3 text-right font-mono text-xs"
                style={{ color }}
              >
                {fmtMoney(f.delta_value, 3)}
              </td>
              <td className="py-1.5 text-right font-mono text-xs text-grey-text">
                {fmtPct(f.relative_change, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
