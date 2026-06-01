"use client";

import type { BarSeriesOption, EChartsOption } from "echarts";
import { useMemo } from "react";

import { EChart } from "@/components/charts/EChart";
import { BRAND } from "@/lib/brand";
import {
  baseTooltip,
  categoryAxis,
  chartGrid,
  valueAxis,
} from "@/lib/chart-base";

export interface BarDatum {
  label: string;
  value: number;
  /** optional override colour for this bar */
  color?: string;
}

/**
 * Horizontal bar chart for rankings (top provinces / sectors / flows).
 * Single series, Bluette by default, value gridlines only.
 */
export function BarChart({
  data,
  valueName,
  height = 320,
  color = BRAND.bluette,
  formatter,
  onSelect,
  highlightLabel,
}: {
  data: BarDatum[];
  valueName?: string;
  height?: number;
  color?: string;
  formatter?: (v: number) => string;
  onSelect?: (label: string) => void;
  highlightLabel?: string | null;
}) {
  const option = useMemo<EChartsOption>(() => {
    // ECharts category axis draws bottom-up; reverse so the largest is on top.
    const labels = data.map((d) => d.label);
    return {
      grid: chartGrid,
      tooltip: {
        ...baseTooltip,
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: (v) =>
          formatter ? formatter(v as number) : String(v),
      },
      xAxis: valueAxis(valueName),
      yAxis: categoryAxis(labels, true),
      series: [
        {
          type: "bar",
          data: data.map((d) => ({
            value: d.value,
            itemStyle: {
              color:
                highlightLabel && d.label === highlightLabel
                  ? BRAND.lime
                  : d.color ?? color,
            },
          })),
          barMaxWidth: 22,
          label: {
            show: data.length <= 12,
            position: "right" as const,
            fontFamily: "var(--font-mono), monospace",
            fontSize: 10,
            color: BRAND.black,
            formatter: (p: { value: number }) =>
              formatter ? formatter(Number(p.value)) : String(p.value),
          } as BarSeriesOption["label"],
        },
      ],
    };
  }, [data, valueName, color, formatter, highlightLabel]);

  const onEvents = useMemo(
    () =>
      onSelect
        ? {
            click: (params: unknown) => {
              const p = params as { name?: string };
              if (p?.name) onSelect(p.name);
            },
          }
        : undefined,
    [onSelect],
  );

  return <EChart option={option} height={height} onEvents={onEvents} />;
}
