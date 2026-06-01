"use client";

import { useMemo, useState } from "react";

import { fmtMoney, fmtPct } from "@/lib/formatters";
import { useRegionLabels } from "@/lib/lookups";
import type { ProvinceSectorLoss } from "@/lib/types";

type SortKey = "total_loss" | "loss_rate" | "direct_loss" | "indirect_loss";

/**
 * Sector-by-province loss table with sortable numeric columns.
 * Rows are region · sector nodes; defaults to the highest total loss first.
 */
export function ProvinceSectorTable({
  rows,
  limit = 20,
  showRegion = true,
}: {
  rows: ProvinceSectorLoss[];
  limit?: number;
  showRegion?: boolean;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("total_loss");
  const region = useRegionLabels();

  const sorted = useMemo(
    () => [...rows].sort((a, b) => b[sortKey] - a[sortKey]).slice(0, limit),
    [rows, sortKey, limit],
  );

  const Th = ({ k, label }: { k: SortKey; label: string }) => (
    <th
      className="cursor-pointer py-2 pr-3 text-right font-medium hover:text-ink"
      onClick={() => setSortKey(k)}
    >
      {label}
      {sortKey === k ? " ▾" : ""}
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-grey-mid text-left text-[11px] uppercase tracking-wide text-grey-text">
            {showRegion && <th className="py-2 pr-3 font-medium">Province</th>}
            <th className="py-2 pr-3 font-medium">Sector</th>
            <Th k="total_loss" label="Total" />
            <Th k="direct_loss" label="Direct" />
            <Th k="indirect_loss" label="Indirect" />
            <Th k="loss_rate" label="Loss rate" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.node_id} className="border-b border-grey-light">
              {showRegion && (
                <td className="py-1.5 pr-3 text-xs" title={region.full(r.region_code)}>
                  {region.abbr(r.region_code)}
                </td>
              )}
              <td className="py-1.5 pr-3 font-mono text-xs">{r.sector_code}</td>
              <td className="py-1.5 pr-3 text-right font-mono text-xs">
                {fmtMoney(r.total_loss, 2)}
              </td>
              <td className="py-1.5 pr-3 text-right font-mono text-xs text-grey-text">
                {fmtMoney(r.direct_loss, 2)}
              </td>
              <td className="py-1.5 pr-3 text-right font-mono text-xs text-grey-text">
                {fmtMoney(r.indirect_loss, 2)}
              </td>
              <td className="py-1.5 text-right font-mono text-xs">
                {fmtPct(r.loss_rate, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
