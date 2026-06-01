"use client";

import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { EChart } from "@/components/charts/EChart";
import { BRAND, DIRECT_LOSS_COLOR, INDIRECT_LOSS_COLOR } from "@/lib/brand";
import {
  baseTooltip,
  categoryAxis,
  chartGrid,
  FONT_SANS,
  valueAxis,
} from "@/lib/chart-base";

export interface DirectIndirectDatum {
  label: string;
  direct: number;
  indirect: number;
}

/**
 * Stacked horizontal bars splitting total loss into direct vs indirect.
 * Direct = darkest Bluette; indirect = mid Bluette (violet).
 */
export function DirectIndirectChart({
  data,
  height = 280,
  formatter,
}: {
  data: DirectIndirectDatum[];
  height?: number;
  formatter?: (v: number) => string;
}) {
  const option = useMemo<EChartsOption>(() => {
    const labels = data.map((d) => d.label);
    const fmt = (v: unknown) => (formatter ? formatter(v as number) : String(v));
    return {
      grid: chartGrid,
      legend: {
        data: ["Direct loss", "Indirect loss"],
        bottom: 0,
        textStyle: { fontFamily: FONT_SANS, fontSize: 11, color: BRAND.black },
        itemWidth: 12,
        itemHeight: 12,
        icon: "rect",
      },
      tooltip: {
        ...baseTooltip,
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: fmt,
      },
      xAxis: valueAxis(),
      yAxis: categoryAxis(labels, true),
      series: [
        {
          name: "Direct loss",
          type: "bar",
          stack: "loss",
          data: data.map((d) => d.direct),
          itemStyle: { color: DIRECT_LOSS_COLOR },
          barMaxWidth: 22,
        },
        {
          name: "Indirect loss",
          type: "bar",
          stack: "loss",
          data: data.map((d) => d.indirect),
          itemStyle: { color: INDIRECT_LOSS_COLOR },
          barMaxWidth: 22,
        },
      ],
    };
  }, [data, formatter]);

  return <EChart option={option} height={height} />;
}
