"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { EChart } from "@/components/charts/EChart";
import { BRAND, FAVORED_COLOR, PENALIZED_COLOR } from "@/lib/brand";
import { baseTooltip, FONT_SANS } from "@/lib/chart-base";
import { fmtMoney } from "@/lib/formatters";
import { useRegionLabels } from "@/lib/lookups";
import type { FlowRecord } from "@/lib/types";

/**
 * Sankey of the most relevant flows. Each side is labelled
 * "region · sector"; origin nodes are suffixed to keep the graph acyclic and
 * readable. Limited to the top N flows by absolute change.
 */
export function FlowSankey({
  flows,
  mode,
  topN = 18,
  height = 460,
}: {
  flows: FlowRecord[];
  mode: "penalized" | "favored";
  topN?: number;
  height?: number;
}) {
  const region = useRegionLabels();
  const option = useMemo<EChartsOption>(() => {
    const sorted = [...flows]
      .sort((a, b) => Math.abs(b.delta_value) - Math.abs(a.delta_value))
      .slice(0, topN);

    const nodeNames = new Set<string>();
    const links = sorted.map((f) => {
      const src = `${region.abbr(f.origin_region)}·${f.origin_sector} ›`;
      const dst = `‹ ${region.abbr(f.destination_region)}·${f.destination_sector}`;
      nodeNames.add(src);
      nodeNames.add(dst);
      return {
        source: src,
        target: dst,
        value: Math.abs(f.delta_value),
        rawDelta: f.delta_value,
      };
    });

    const color = mode === "penalized" ? PENALIZED_COLOR : FAVORED_COLOR;

    return {
      tooltip: {
        ...baseTooltip,
        trigger: "item",
        formatter: (p: unknown) => {
          const param = p as {
            dataType?: string;
            data?: { source?: string; target?: string; rawDelta?: number };
            name?: string;
          };
          if (param.dataType === "edge" && param.data) {
            return `${param.data.source} → ${param.data.target}<br/><b>${fmtMoney(
              param.data.rawDelta,
              3,
            )}</b>`;
          }
          return param.name ?? "";
        },
      },
      series: [
        {
          type: "sankey",
          left: 8,
          right: 8,
          top: 12,
          bottom: 12,
          nodeWidth: 12,
          nodeGap: 8,
          draggable: false,
          emphasis: { focus: "adjacency" },
          data: Array.from(nodeNames).map((name) => ({
            name,
            itemStyle: { color: BRAND.bluette900, borderColor: BRAND.bluette900 },
          })),
          links: links.map((l) => ({
            ...l,
            lineStyle: { color, opacity: 0.4 },
          })),
          label: {
            fontFamily: FONT_SANS,
            fontSize: 10,
            color: BRAND.black,
          },
        },
      ],
    };
  }, [flows, mode, topN, region]);

  return <EChart option={option} height={height} />;
}
