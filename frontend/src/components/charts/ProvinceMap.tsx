"use client";

import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import { useMemo } from "react";

import { EChart } from "@/components/charts/EChart";
import { BRAND, MAP_RAMP } from "@/lib/brand";
import { extent } from "@/lib/color-scale";
import { baseTooltip, FONT_SANS } from "@/lib/chart-base";
import type { ProvinceFeatureCollection } from "@/lib/types";

export interface MapValue {
  /** join key: NUTS region_code */
  regionCode: string;
  value: number | null;
  /** preformatted tooltip rows */
  tooltip: { label: string; value: string }[];
  name: string;
}

const MAP_NAME = "italy-provinces";
let mapRegistered = false;

/**
 * Register the province GeoJSON as a named ECharts map. Done synchronously at
 * render time (guarded, idempotent) so the map geometry exists BEFORE the child
 * EChart runs its setOption effect — registering inside a useEffect runs too
 * late (child effects fire before parent effects) and leaves the map blank.
 */
function ensureMapRegistered(geojson: ProvinceFeatureCollection) {
  if (mapRegistered) return;
  if (!geojson?.features?.length) return;
  echarts.registerMap(MAP_NAME, geojson as never);
  mapRegistered = true;
}

/**
 * Italian province choropleth rendered with ECharts' geo map. Colours provinces
 * by the supplied metric; hover shows a tooltip, click selects, and the selected
 * province gets a Lime outline. Uses ECharts (not a WebGL basemap) for
 * reliability in this static, no-tile-server setup.
 */
export function ProvinceMap({
  geojson,
  values,
  selectedRegion,
  onSelect,
  height = 460,
}: {
  geojson: ProvinceFeatureCollection;
  values: Map<string, MapValue>;
  selectedRegion?: string | null;
  onSelect?: (regionCode: string) => void;
  height?: number;
}) {
  ensureMapRegistered(geojson);

  const option = useMemo<EChartsOption>(() => {
    const vals = Array.from(values.values())
      .map((v) => v.value)
      .filter((v): v is number => v != null);
    const [min, max] = extent(vals);

    const data = geojson.features.map((f) => {
      const rc = f.properties.region_code;
      const mv = values.get(rc);
      const selected = selectedRegion === rc;
      return {
        name: rc,
        // ECharts treats NaN as "no data" (rendered with the default areaColor).
        value: mv?.value ?? NaN,
        itemStyle: selected
          ? { borderColor: BRAND.lime, borderWidth: 2.5, areaColor: undefined }
          : {},
      };
    });

    return {
      tooltip: {
        ...baseTooltip,
        trigger: "item",
        formatter: (p: unknown) => {
          const param = p as { name: string };
          const mv = values.get(param.name);
          const title = mv?.name ?? param.name;
          const rows =
            mv?.tooltip
              .map(
                (r) =>
                  `<div style="display:flex;justify-content:space-between;gap:16px"><span>${r.label}</span><b>${r.value}</b></div>`,
              )
              .join("") ?? "";
          return `<div style="font-weight:600;margin-bottom:4px;border-bottom:1px solid ${BRAND.greyMid};padding-bottom:3px">${title}</div>${rows}`;
        },
      },
      visualMap: {
        type: "continuous",
        min,
        max: max > min ? max : min + 1,
        calculable: true,
        orient: "vertical",
        left: 8,
        bottom: 16,
        itemWidth: 10,
        itemHeight: 110,
        textStyle: { color: BRAND.greyText, fontSize: 10, fontFamily: FONT_SANS },
        inRange: { color: MAP_RAMP as unknown as string[] },
      },
      series: [
        {
          type: "map",
          map: MAP_NAME,
          roam: true,
          scaleLimit: { min: 1, max: 8 },
          // Centre the map and size it to the box while preserving the true
          // geographic aspect ratio (prevents horizontal/vertical stretching).
          // Nudged slightly right so the visualMap legend sits in the left margin.
          layoutCenter: ["54%", "50%"],
          layoutSize: "98%",
          aspectScale: 0.78,
          nameProperty: "region_code",
          itemStyle: {
            areaColor: BRAND.greyLight,
            borderColor: BRAND.white,
            borderWidth: 0.5,
          },
          emphasis: {
            label: { show: false },
            itemStyle: { borderColor: BRAND.black, borderWidth: 1 },
          },
          select: { disabled: true },
          label: { show: false },
          data,
        },
      ],
    };
  }, [geojson, values, selectedRegion]);

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
