"use client";

import { useMemo } from "react";

import { BarChart } from "@/components/charts/BarChart";
import { ProvinceMap, type MapValue } from "@/components/charts/ProvinceMap";
import { ChartCard } from "@/components/cards/ChartCard";
import { ExplanationCard } from "@/components/cards/ExplanationCard";
import { ControlPanel } from "@/components/layout/ControlPanel";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProvinceSectorTable } from "@/components/tables/ProvinceSectorTable";
import {
  useProvinceGeoJson,
  useProvinceSectorLosses,
  useSectorLosses,
} from "@/lib/data";
import { fmtMoney, fmtPct } from "@/lib/formatters";
import { useRegionLabels, useSectorLabels } from "@/lib/lookups";
import { useScenario } from "@/lib/scenario-context";

export function SectorImpactPanel() {
  const { scenarioId, sectorCode } = useScenario();
  const { data: geo } = useProvinceGeoJson();
  const { data: sectors } = useSectorLosses(scenarioId);
  const { data: psl } = useProvinceSectorLosses(scenarioId);
  const region = useRegionLabels();
  const sectorLabels = useSectorLabels();

  const byLoss = useMemo(
    () =>
      (sectors ?? [])
        .slice()
        .sort((a, b) => b.total_loss - a.total_loss)
        .slice(0, 15)
        .map((s) => ({ label: s.sector_code, value: s.total_loss })),
    [sectors],
  );

  const byRate = useMemo(
    () =>
      (sectors ?? [])
        .slice()
        .sort((a, b) => b.loss_rate - a.loss_rate)
        .slice(0, 15)
        .map((s) => ({ label: s.sector_code, value: s.loss_rate })),
    [sectors],
  );

  // Default selected sector = highest loss.
  const effectiveSector = useMemo(
    () => sectorCode ?? byLoss[0]?.label ?? null,
    [sectorCode, byLoss],
  );

  const sectorRows = useMemo(
    () => (psl ?? []).filter((r) => r.sector_code === effectiveSector),
    [psl, effectiveSector],
  );

  const sectorMapValues = useMemo(() => {
    const map = new Map<string, MapValue>();
    for (const r of sectorRows) {
      map.set(r.region_code, {
        regionCode: r.region_code,
        name: region.full(r.region_code),
        value: r.total_loss,
        tooltip: [
          { label: "Sector", value: r.sector_code },
          { label: "Total loss", value: fmtMoney(r.total_loss, 2) },
          { label: "Loss rate", value: fmtPct(r.loss_rate, 2) },
          { label: "Supply shock", value: fmtPct(r.supply_shock, 2) },
        ],
      });
    }
    return map;
  }, [sectorRows, region]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Sectoral Impact"
        intro="How production losses vary across economic sectors, and where a given sector is hit hardest geographically. Choose a sector below to map its losses by province."
      />

      <div className="rounded-card border border-grey-mid bg-paper p-3">
        <ControlPanel showHazard={false} showScenario={false} showSector />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          title="Sector losses"
          subtitle="Total production loss by sector (top 15)"
          note="Source: Supply-shock MRIO model, static scenario outputs."
        >
          <BarChart data={byLoss} height={360} formatter={(v) => fmtMoney(v)} />
        </ChartCard>
        <ChartCard
          title="Sector loss rates"
          subtitle="Loss as a share of the sector's pre-shock output (top 15)"
        >
          <BarChart data={byRate} height={360} formatter={(v) => fmtPct(v, 2)} />
        </ChartCard>
      </div>

      <ChartCard
        title={`Selected sector — loss by province${
          effectiveSector ? ` (${sectorLabels.full(effectiveSector)})` : ""
        }`}
        subtitle="Geographic distribution of a single sector's losses. Change the sector in the control above."
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {geo ? (
            <ProvinceMap
              geojson={geo}
              values={sectorMapValues}
              height={420}
            />
          ) : (
            <div className="h-[420px] animate-pulse rounded-card bg-grey-light" />
          )}
          <ProvinceSectorTable rows={sectorRows} limit={15} />
        </div>
      </ChartCard>

      <ExplanationCard emphasis title="Sector vulnerability assumptions">
        <p>
          Sector-level outcomes combine each sector&apos;s direct hazard
          vulnerability (an expert-calibrated factor mapping exposure to
          interruption) with its position in the input-output network.
          Highly-connected upstream sectors propagate losses widely even when
          their own direct exposure is modest. See the Methodology and Data
          &amp; assumptions pages for the vulnerability factors used.
        </p>
      </ExplanationCard>
    </div>
  );
}
