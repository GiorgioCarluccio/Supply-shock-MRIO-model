"use client";

import { useMemo } from "react";

import { BarChart } from "@/components/charts/BarChart";
import { ProvinceMap } from "@/components/charts/ProvinceMap";
import { ChartCard } from "@/components/cards/ChartCard";
import { ExplanationCard } from "@/components/cards/ExplanationCard";
import { KpiCard } from "@/components/cards/KpiCard";
import { ControlPanel } from "@/components/layout/ControlPanel";
import { PageHeader } from "@/components/layout/PageHeader";
import { FlowTable } from "@/components/tables/FlowTable";
import {
  useProvinceGeoJson,
  useProvinceMetrics,
  useProvinceSectorLosses,
  useTopFavoredFlows,
  useTopPenalizedFlows,
} from "@/lib/data";
import { fmtMoney, fmtPct, fmtShock } from "@/lib/formatters";
import { buildMapValues } from "@/lib/map-values";
import { useScenario } from "@/lib/scenario-context";

export function RegionalExposurePanel() {
  const { scenarioId, regionCode, setRegionCode } = useScenario();
  const { data: geo } = useProvinceGeoJson();
  const { data: metrics } = useProvinceMetrics(scenarioId);
  const { data: psl } = useProvinceSectorLosses(scenarioId);
  const { data: penalized } = useTopPenalizedFlows(scenarioId);
  const { data: favored } = useTopFavoredFlows(scenarioId);

  // Effective province: explicit selection, else the most-impacted one.
  const effectiveRegion = useMemo(() => {
    if (regionCode) return regionCode;
    const top = (metrics ?? [])
      .slice()
      .sort((a, b) => b.total_loss - a.total_loss)[0];
    return top?.region_code ?? null;
  }, [regionCode, metrics]);

  const prov = useMemo(
    () => metrics?.find((m) => m.region_code === effectiveRegion),
    [metrics, effectiveRegion],
  );

  const mapValues = useMemo(
    () => (metrics ? buildMapValues(metrics, "total_loss") : new Map()),
    [metrics],
  );

  const topSectors = useMemo(
    () =>
      (psl ?? [])
        .filter((r) => r.region_code === effectiveRegion)
        .sort((a, b) => b.total_loss - a.total_loss)
        .slice(0, 10)
        .map((r) => ({ label: r.sector_code, value: r.total_loss })),
    [psl, effectiveRegion],
  );

  const outgoing = useMemo(
    () => (penalized ?? []).filter((f) => f.origin_region === effectiveRegion),
    [penalized, effectiveRegion],
  );
  const incoming = useMemo(
    () =>
      (penalized ?? []).filter((f) => f.destination_region === effectiveRegion),
    [penalized, effectiveRegion],
  );
  const favoredHere = useMemo(
    () =>
      (favored ?? []).filter(
        (f) =>
          f.origin_region === effectiveRegion ||
          f.destination_region === effectiveRegion,
      ),
    [favored, effectiveRegion],
  );

  return (
    <div className="space-y-5">
      <PageHeader
        title="Regional Exposure & Impact"
        intro="Select a province to see its direct hazard exposure, the calibrated shocks applied, and the direct vs indirect losses transmitted through the network. Pick a province below or click one on the map."
      />

      <div className="rounded-card border border-grey-mid bg-paper p-3">
        <ControlPanel showHazard={false} showScenario={false} showProvince />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <ChartCard
          title="Select a province"
          subtitle="Coloured by total production loss"
        >
          {geo ? (
            <ProvinceMap
              geojson={geo}
              values={mapValues}
              selectedRegion={effectiveRegion}
              onSelect={setRegionCode}
              height={420}
            />
          ) : (
            <div className="h-[420px] animate-pulse rounded-card bg-grey-light" />
          )}
        </ChartCard>

        <div className="xl:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold text-ink">
            {prov?.province_name ?? "—"}{" "}
            <span className="text-sm font-normal text-grey-text">
              {prov?.province_abbr ?? prov?.region_code}
            </span>
          </h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <KpiCard
              label="Hazard exposure"
              value={fmtShock(prov?.raw_exposure)}
              sublabel="weight"
            />
            <KpiCard label="Supply shock" value={fmtShock(prov?.mean_supply_shock)} sublabel="mean" />
            <KpiCard label="Demand shock" value={fmtShock(prov?.mean_demand_shock)} sublabel="mean" />
            <KpiCard
              label="Equivalent stop days"
              value={prov?.equivalent_stop_days != null ? prov.equivalent_stop_days.toFixed(2) : "—"}
              sublabel={`base ${prov?.base_interruption_days ?? "—"} d`}
            />
            <KpiCard accent label="Total loss" value={fmtMoney(prov?.total_loss)} />
            <KpiCard label="Direct loss" value={fmtMoney(prov?.direct_loss)} />
            <KpiCard label="Indirect loss" value={fmtMoney(prov?.indirect_loss)} />
            <KpiCard
              label="Indirect ratio"
              value={fmtPct(prov?.indirect_exposure_ratio, 1)}
              sublabel="of total loss"
            />
          </div>
          <ExplanationCard emphasis>
            <p>
              In {prov?.province_name ?? "this province"},{" "}
              <strong>{fmtPct(prov?.indirect_exposure_ratio, 0)}</strong> of the
              total production loss is <strong>indirect</strong> — transmitted
              from shocks elsewhere in the input-output network rather than
              originating from the province&apos;s own direct exposure.
            </p>
          </ExplanationCard>
        </div>
      </div>

      <ChartCard
        title="Top affected sectors in province"
        subtitle="Production loss by sector within the selected province"
      >
        <BarChart data={topSectors} height={300} formatter={(v) => fmtMoney(v, 2)} />
      </ChartCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          title="Most penalised outgoing flows"
          subtitle="Flows originating in this province with the largest losses"
        >
          <FlowTable flows={outgoing} mode="penalized" limit={10} />
        </ChartCard>
        <ChartCard
          title="Most penalised incoming flows"
          subtitle="Flows into this province with the largest losses"
        >
          <FlowTable flows={incoming} mode="penalized" limit={10} />
        </ChartCard>
      </div>

      <ChartCard
        title="Favoured / reallocated flows involving this province"
        subtitle="Flows that increase as demand reallocates around interruptions"
      >
        <FlowTable flows={favoredHere} mode="favored" limit={10} />
      </ChartCard>
    </div>
  );
}
