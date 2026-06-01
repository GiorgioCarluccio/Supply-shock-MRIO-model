"use client";

import { useMemo, useState } from "react";

import { BarChart } from "@/components/charts/BarChart";
import { DirectIndirectChart } from "@/components/charts/DirectIndirectChart";
import { ProvinceMap } from "@/components/charts/ProvinceMap";
import { Caveat } from "@/components/cards/Caveat";
import { ChartCard } from "@/components/cards/ChartCard";
import { ExplanationCard } from "@/components/cards/ExplanationCard";
import { KpiCard } from "@/components/cards/KpiCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { Segmented } from "@/components/ui/segmented";
import {
  useProvinceGeoJson,
  useProvinceMetrics,
  useScenarioIndex,
  useSectorLosses,
} from "@/lib/data";
import { HAZARD_META, SEVERITY_LABELS } from "@/lib/constants";
import { fmtMoney, fmtPct, fmtShock } from "@/lib/formatters";
import { buildMapValues, MAP_METRIC_LABELS } from "@/lib/map-values";
import { useScenario } from "@/lib/scenario-context";
import type { MapMetric } from "@/lib/types";

export function ExecutiveOverview() {
  const { scenarioId, selected, hazard, regionCode, setRegionCode } =
    useScenario();
  const { data: index } = useScenarioIndex();
  const { data: geo } = useProvinceGeoJson();
  const { data: metrics } = useProvinceMetrics(scenarioId);
  const { data: sectors } = useSectorLosses(scenarioId);

  const [mapMetric, setMapMetric] = useState<MapMetric>("total_loss");

  const mapValues = useMemo(
    () => (metrics ? buildMapValues(metrics, mapMetric) : new Map()),
    [metrics, mapMetric],
  );

  const topExposed = useMemo(
    () =>
      (metrics ?? [])
        .filter((m) => m.raw_exposure != null)
        .sort((a, b) => (b.raw_exposure ?? 0) - (a.raw_exposure ?? 0))
        .slice(0, 10)
        .map((m) => ({ label: m.province_abbr ?? m.region_code, value: m.raw_exposure ?? 0 })),
    [metrics],
  );

  const topImpacted = useMemo(
    () =>
      (metrics ?? [])
        .slice()
        .sort((a, b) => b.total_loss - a.total_loss)
        .slice(0, 10)
        .map((m) => ({ label: m.province_abbr ?? m.region_code, value: m.total_loss })),
    [metrics],
  );

  const topSectors = useMemo(
    () =>
      (sectors ?? [])
        .slice()
        .sort((a, b) => b.total_loss - a.total_loss)
        .slice(0, 10)
        .map((s) => ({ label: s.sector_code, value: s.total_loss })),
    [sectors],
  );

  const directIndirect = useMemo(
    () =>
      selected
        ? [
            {
              label: "Total",
              direct: selected.total_direct_loss,
              indirect: selected.total_indirect_loss,
            },
          ]
        : [],
    [selected],
  );

  const mostExposed = useMemo(
    () =>
      (metrics ?? [])
        .filter((m) => m.raw_exposure != null)
        .sort((a, b) => (b.raw_exposure ?? 0) - (a.raw_exposure ?? 0))[0],
    [metrics],
  );
  const mostImpactedSector = useMemo(
    () => (sectors ?? []).slice().sort((a, b) => b.total_loss - a.total_loss)[0],
    [sectors],
  );

  const hazardLabel = HAZARD_META[hazard]?.label ?? hazard;
  const sevLabel = selected ? SEVERITY_LABELS[selected.severity] ?? selected.severity : "";

  return (
    <div className="space-y-5">
      <PageHeader
        title="Executive Overview"
        intro={
          <>
            Immediate reading of the selected hazard scenario across Italian
            provinces. Figures are static precomputed estimates of{" "}
            <strong>business-interruption</strong> losses propagated through the
            provincial input-output network — not physical asset damage.
          </>
        }
      />

      {index?.runtime_caveat && <Caveat>{index.runtime_caveat}</Caveat>}

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <KpiCard
          accent
          label="Total production loss"
          value={fmtMoney(selected?.total_loss)}
          sublabel={`${hazardLabel} · ${sevLabel}`}
        />
        <KpiCard
          label="Loss rate"
          value={fmtPct(selected?.loss_rate_total, 2)}
          sublabel="of total output"
        />
        <KpiCard
          label="Direct loss"
          value={fmtMoney(selected?.total_direct_loss)}
          sublabel="at shocked nodes"
        />
        <KpiCard
          label="Indirect loss"
          value={fmtMoney(selected?.total_indirect_loss)}
          sublabel="network propagation"
        />
        <KpiCard
          label="Most exposed province"
          value={mostExposed?.province_abbr ?? "—"}
          sublabel={mostExposed ? mostExposed.province_name ?? "" : ""}
        />
        <KpiCard
          label="Most impacted sector"
          value={mostImpactedSector?.sector_code ?? "—"}
          sublabel={
            mostImpactedSector ? fmtMoney(mostImpactedSector.total_loss) : ""
          }
        />
      </div>

      <ExplanationCard emphasis>
        <p>
          The <strong>{hazardLabel.toLowerCase()}</strong> scenario applies
          calibrated supply and demand shocks to{" "}
          {selected?.n_nodes_shocked?.toLocaleString() ?? "—"} of{" "}
          {selected?.n_nodes?.toLocaleString() ?? "—"} province-sector nodes.
          Indirect losses dominate the total
          {selected
            ? ` (a ${selected.total_over_direct_multiplier.toFixed(1)}× multiplier over direct losses)`
            : ""}
          , reflecting how interruptions transmit through inter-provincial and
          inter-sectoral input-output dependencies.
        </p>
      </ExplanationCard>

      {/* Map + rankings */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ChartCard
            title="Impact across Italian provinces"
            subtitle={`Provinces coloured by ${MAP_METRIC_LABELS[mapMetric].toLowerCase()}. Click a province to focus it.`}
            note="Source: Supply-shock MRIO model, static scenario outputs."
            actions={
              <Segmented<MapMetric>
                value={mapMetric}
                onChange={setMapMetric}
                options={[
                  { value: "total_loss", label: "Loss" },
                  { value: "loss_rate", label: "Loss rate" },
                  { value: "raw_exposure", label: "Exposure" },
                  { value: "mean_supply_shock", label: "Supply shock" },
                ]}
              />
            }
          >
            {geo ? (
              <ProvinceMap
                geojson={geo}
                values={mapValues}
                selectedRegion={regionCode}
                onSelect={(rc) => setRegionCode(rc === regionCode ? null : rc)}
                height={540}
              />
            ) : (
              <div className="h-[540px] animate-pulse rounded-card bg-grey-light" />
            )}
          </ChartCard>
        </div>

        <div className="space-y-4">
          <ChartCard
            title="Direct vs indirect loss"
            subtitle="How much of the total is transmitted through the network"
          >
            <DirectIndirectChart
              data={directIndirect}
              height={120}
              formatter={(v) => fmtMoney(v)}
            />
          </ChartCard>
          <ChartCard
            title="Top impacted sectors"
            subtitle="Largest production loss by sector"
          >
            <BarChart
              data={topSectors}
              height={260}
              formatter={(v) => fmtMoney(v)}
            />
          </ChartCard>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          title="Most exposed provinces"
          subtitle="Direct hazard exposure weight (pre-propagation)"
          note="Exposure reflects physical hazard before economic propagation."
        >
          <BarChart
            data={topExposed}
            height={300}
            formatter={(v) => fmtShock(v)}
          />
        </ChartCard>
        <ChartCard
          title="Most impacted provinces"
          subtitle="Total production loss after propagation"
        >
          <BarChart
            data={topImpacted}
            height={300}
            formatter={(v) => fmtMoney(v)}
            onSelect={(label) => {
              const m = metrics?.find((x) => x.province_abbr === label);
              if (m) setRegionCode(m.region_code);
            }}
          />
        </ChartCard>
      </div>
    </div>
  );
}
