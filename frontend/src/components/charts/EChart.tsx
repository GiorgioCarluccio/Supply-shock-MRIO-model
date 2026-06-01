"use client";

import * as echarts from "echarts";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Thin ECharts wrapper. Initialises a chart instance, applies the option,
 * and handles resize / disposal. All option construction lives in the
 * individual chart components so the brand styling is explicit there.
 */
export function EChart({
  option,
  className,
  height = 320,
  onEvents,
}: {
  option: echarts.EChartsOption;
  className?: string;
  height?: number;
  onEvents?: Record<string, (params: unknown) => void>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(option, true);
  }, [option]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !onEvents) return;
    const handlers = Object.entries(onEvents);
    handlers.forEach(([evt, fn]) => chart.on(evt, fn as never));
    return () => {
      handlers.forEach(([evt, fn]) => chart.off(evt, fn as never));
    };
  }, [onEvents]);

  return (
    <div
      ref={ref}
      className={cn("w-full", className)}
      style={{ height }}
      role="img"
    />
  );
}
