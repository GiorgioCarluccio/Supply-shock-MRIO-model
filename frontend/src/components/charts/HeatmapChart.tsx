"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { EChart } from "@/components/charts/EChart";
import { BRAND } from "@/lib/brand";
import { axisLabel, baseTooltip, FONT_MONO } from "@/lib/chart-base";
import { fmtMoney } from "@/lib/formatters";

export interface HeatCell {
  origin: string;
  destination: string;
  value: number;
}

/**
 * Diverging heatmap for flow-change matrices (province↔province, sector↔sector).
 * Negative (penalised) -> Bluette; positive (favoured) -> green.
 * Origins on the Y axis, destinations on the X axis.
 */
export function HeatmapChart({
  cells,
  height = 520,
}: {
  cells: HeatCell[];
  height?: number;
}) {
  const option = useMemo<EChartsOption>(() => {
    const origins = Array.from(new Set(cells.map((c) => c.origin))).sort();
    const dests = Array.from(new Set(cells.map((c) => c.destination))).sort();
    const oIdx = new Map(origins.map((o, i) => [o, i]));
    const dIdx = new Map(dests.map((d, i) => [d, i]));
    let maxAbs = 0;
    for (const c of cells) maxAbs = Math.max(maxAbs, Math.abs(c.value));
    const data = cells.map((c) => [
      dIdx.get(c.destination) as number,
      oIdx.get(c.origin) as number,
      c.value,
    ]);

    return {
      grid: { left: 8, right: 16, top: 8, bottom: 60, containLabel: true },
      tooltip: {
        ...baseTooltip,
        trigger: "item",
        formatter: (p: unknown) => {
          const param = p as { value: [number, number, number] };
          const [d, o, v] = param.value;
          return `${origins[o]} → ${dests[d]}<br/><b>${fmtMoney(v, 3)}</b>`;
        },
      },
      xAxis: {
        type: "category",
        data: dests,
        name: "destination",
        nameLocation: "middle",
        nameGap: 42,
        nameTextStyle: { color: BRAND.greyText, fontSize: 11 },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: BRAND.greyMid } },
        axisTick: { show: false },
        axisLabel: { ...axisLabel, rotate: 60, fontFamily: FONT_MONO },
      },
      yAxis: {
        type: "category",
        data: origins,
        name: "origin",
        nameTextStyle: { color: BRAND.greyText, fontSize: 11 },
        splitArea: { show: false },
        axisLine: { lineStyle: { color: BRAND.greyMid } },
        axisTick: { show: false },
        axisLabel: { ...axisLabel, fontFamily: FONT_MONO },
      },
      visualMap: {
        min: -maxAbs,
        max: maxAbs,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        itemWidth: 12,
        itemHeight: 120,
        precision: 1,
        textStyle: { color: BRAND.greyText, fontSize: 10 },
        inRange: {
          color: [BRAND.bluette, "#B79BE6", BRAND.greyLight, "#A9D77A", FAVORED],
        },
      },
      series: [
        {
          type: "heatmap",
          data,
          emphasis: { itemStyle: { borderColor: BRAND.black, borderWidth: 1 } },
          progressive: 2000,
        },
      ],
    };
  }, [cells]);

  return <EChart option={option} height={height} />;
}

const FAVORED = "#7BBF3F";
