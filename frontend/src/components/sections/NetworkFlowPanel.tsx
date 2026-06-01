"use client";

import { useMemo, useState } from "react";

import { FlowSankey } from "@/components/charts/FlowSankey";
import { HeatmapChart, type HeatCell } from "@/components/charts/HeatmapChart";
import { ChartCard } from "@/components/cards/ChartCard";
import { ExplanationCard } from "@/components/cards/ExplanationCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { FlowTable } from "@/components/tables/FlowTable";
import { Segmented } from "@/components/ui/segmented";
import {
  useProvinceFlowHeatmap,
  useSectorFlowHeatmap,
  useTopFavoredFlows,
  useTopPenalizedFlows,
} from "@/lib/data";
import { useRegionLabels } from "@/lib/lookups";
import { useScenario } from "@/lib/scenario-context";

type HeatMode = "province" | "sector";

/** Keep the heatmap legible: restrict to the top-N categories by |Δ|. */
function topCells(
  cells: { o: string; d: string; v: number }[],
  topN: number,
): HeatCell[] {
  const weight = new Map<string, number>();
  for (const c of cells) {
    weight.set(c.o, (weight.get(c.o) ?? 0) + Math.abs(c.v));
    weight.set(c.d, (weight.get(c.d) ?? 0) + Math.abs(c.v));
  }
  const keep = new Set(
    Array.from(weight.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, topN)
      .map(([k]) => k),
  );
  return cells
    .filter((c) => keep.has(c.o) && keep.has(c.d) && c.v !== 0)
    .map((c) => ({ origin: c.o, destination: c.d, value: c.v }));
}

export function NetworkFlowPanel() {
  const { scenarioId } = useScenario();
  const { data: penalized } = useTopPenalizedFlows(scenarioId);
  const { data: favored } = useTopFavoredFlows(scenarioId);
  const { data: provHeat } = useProvinceFlowHeatmap(scenarioId);
  const { data: sectorHeat } = useSectorFlowHeatmap(scenarioId);
  const region = useRegionLabels();

  const [heatMode, setHeatMode] = useState<HeatMode>("sector");

  const heatCells = useMemo<HeatCell[]>(() => {
    if (heatMode === "province") {
      return topCells(
        (provHeat ?? []).map((c) => ({
          o: region.abbr(c.origin_region_code),
          d: region.abbr(c.destination_region_code),
          v: c.delta_value,
        })),
        18,
      );
    }
    return topCells(
      (sectorHeat ?? []).map((c) => ({
        o: c.origin_sector_code,
        d: c.destination_sector_code,
        v: c.delta_value,
      })),
      22,
    );
  }, [heatMode, provHeat, sectorHeat, region]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Network Flows"
        intro="How the shock propagates and reconfigures economic flows. Penalised flows shrink as interruptions ripple downstream; favoured flows grow where demand reallocates around them."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          title="Top penalised flows"
          subtitle="Largest reductions in flow value (origin → destination)"
        >
          <FlowTable flows={penalized ?? []} mode="penalized" limit={15} />
        </ChartCard>
        <ChartCard
          title="Top favoured / reallocated flows"
          subtitle="Largest increases in flow value"
        >
          <FlowTable flows={favored ?? []} mode="favored" limit={15} />
        </ChartCard>
      </div>

      <ChartCard
        title="Most relevant penalised flows"
        subtitle="Sankey of the 18 largest flow reductions (region·sector → region·sector)"
        note="Limited to the top flows for readability; see the tables above for the full ranking."
      >
        <FlowSankey flows={penalized ?? []} mode="penalized" topN={18} />
      </ChartCard>

      <ChartCard
        title="Flow-change heatmap"
        subtitle={
          heatMode === "province"
            ? "Net change in inter-provincial flows (top provinces by activity)"
            : "Net change in inter-sectoral flows (top sectors by activity)"
        }
        note="Bluette = penalised (net reduction); green = favoured (net increase)."
        actions={
          <Segmented<HeatMode>
            value={heatMode}
            onChange={setHeatMode}
            options={[
              { value: "sector", label: "Sector ↔ sector" },
              { value: "province", label: "Province ↔ province" },
            ]}
          />
        }
      >
        {heatCells.length ? (
          <HeatmapChart cells={heatCells} height={560} />
        ) : (
          <div className="h-[560px] animate-pulse rounded-card bg-grey-light" />
        )}
      </ChartCard>

      <ExplanationCard emphasis>
        <p>
          Flow reconfiguration is a second-order effect: as shocked sectors cut
          output, their trading partners adjust sourcing. The diverging heatmap
          shows where flows net-shrink (penalised) versus net-grow (favoured)
          as the network re-balances around the interruption.
        </p>
      </ExplanationCard>
    </div>
  );
}
