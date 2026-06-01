"use client";

import { useMemo } from "react";

import { Caveat } from "@/components/cards/Caveat";
import { ChartCard } from "@/components/cards/ChartCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  useDataStatus,
  useScenarioIndex,
  useSectorVulnerability,
} from "@/lib/data";
import { HAZARD_META, SEVERITY_LABELS } from "@/lib/constants";
import { fmtPct } from "@/lib/formatters";

const DATA_CAVEATS = [
  "Physical hazard exposure is transformed into business-interruption shock through assumptions on interruption days and sector vulnerability.",
  "Flood and landslide exposure reflect shares of local business units exposed / risk-classified.",
  "Heatwave exposure is derived from E-OBS maximum-temperature hot-day indicators.",
  "The model estimates short-term production interruption and network propagation, not physical asset loss.",
];

const DATA_SOURCES = [
  {
    title: "Climate hazard — heatwave",
    body: "E-OBS daily maximum-temperature grids (1991–2025); hot-day indicators aggregated to provinces.",
  },
  {
    title: "Climate hazard — flood & landslide",
    body: "Provincial Inventory of Risk (PIR) shares of business units exposed / in risk classes (flood; landslide P1–P4).",
  },
  {
    title: "Geography",
    body: "ISTAT 2024 provincial / metropolitan-city boundaries (ProvCM01012024), reprojected to WGS84.",
  },
  {
    title: "Economic network",
    body: "Provincial Social Accounting Matrix / input-output table (6,462 province-sector nodes, 62 sectors).",
  },
];

export function DataAssumptionsPanel() {
  const { data: status } = useDataStatus();
  const { data: index } = useScenarioIndex();
  const { data: vuln } = useSectorVulnerability();

  const statusRows = useMemo(
    () =>
      status
        ? [
            ["Climate exposure", status.climate_exposure],
            ["Shock calibration", status.shock_calibration],
            ["SAM model inputs", status.sam_model_inputs],
            ["Simulation outputs", status.simulation_outputs],
            ["Frontend mode", status.frontend_mode],
          ]
        : [],
    [status],
  );

  // One representative vulnerability per (sector, hazard) — show distinct values.
  const vulnByHazard = useMemo(() => {
    const m = new Map<string, { min: number; max: number }>();
    for (const v of vuln ?? []) {
      const cur = m.get(v.hazard) ?? { min: Infinity, max: -Infinity };
      cur.min = Math.min(cur.min, v.sector_vulnerability);
      cur.max = Math.max(cur.max, v.sector_vulnerability);
      m.set(v.hazard, cur);
    }
    return Array.from(m.entries());
  }, [vuln]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Data & Assumptions"
        intro="The data sources, calibration assumptions, and caveats behind the scenario estimates shown in this dashboard."
      />

      {/* Data status */}
      <Card>
        <CardHeader>
          <CardTitle>Data status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {statusRows.map(([k, v]) => (
              <div
                key={k}
                className="rounded-card border border-grey-mid bg-grey-light px-3 py-2"
              >
                <div className="text-[10px] uppercase tracking-wide text-grey-text">
                  {k}
                </div>
                <div className="mt-0.5 text-sm font-semibold text-ink">{v}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Data sources */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {DATA_SOURCES.map((s) => (
          <Card key={s.title}>
            <CardHeader>
              <CardTitle>{s.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-grey-text">{s.body}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Scenario assumptions */}
      <ChartCard
        title="Scenario assumptions"
        subtitle="Calibration parameters per precomputed scenario"
        note="Shock caps bound how large any single supply/demand shock can be."
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-grey-mid text-left text-[11px] uppercase tracking-wide text-grey-text">
                <th className="py-2 pr-3 font-medium">Hazard</th>
                <th className="py-2 pr-3 font-medium">Severity</th>
                <th className="py-2 pr-3 text-right font-medium">Base interruption (d)</th>
                <th className="py-2 pr-3 text-right font-medium">Demand λ</th>
                <th className="py-2 pr-3 text-right font-medium">Max supply shock</th>
                <th className="py-2 pr-3 text-right font-medium">Max demand shock</th>
                <th className="py-2 text-right font-medium">Iterations</th>
              </tr>
            </thead>
            <tbody>
              {(index?.summaries ?? []).map((s) => (
                <tr key={s.scenario_id} className="border-b border-grey-light">
                  <td className="py-1.5 pr-3">{HAZARD_META[s.hazard]?.label ?? s.hazard}</td>
                  <td className="py-1.5 pr-3">{SEVERITY_LABELS[s.severity] ?? s.severity}</td>
                  <td className="py-1.5 pr-3 text-right font-mono text-xs">{s.base_interruption_days}</td>
                  <td className="py-1.5 pr-3 text-right font-mono text-xs">{s.demand_pass_through_lambda}</td>
                  <td className="py-1.5 pr-3 text-right font-mono text-xs">{fmtPct(s.max_supply_shock, 0)}</td>
                  <td className="py-1.5 pr-3 text-right font-mono text-xs">{fmtPct(s.max_demand_shock, 0)}</td>
                  <td className="py-1.5 text-right font-mono text-xs">{s.iterations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>

      {/* Sector vulnerability */}
      <ChartCard
        title="Sector vulnerability assumptions"
        subtitle="Expert-calibrated factors mapping exposure to interruption, by hazard"
        note="Vulnerability factors are editable placeholders in the calibration pipeline; ranges shown across sectors."
      >
        <div className="flex flex-wrap gap-3">
          {vulnByHazard.map(([hazard, range]) => (
            <div
              key={hazard}
              className="rounded-card border border-grey-mid bg-grey-light px-4 py-3"
            >
              <div className="text-xs font-semibold text-ink">
                {HAZARD_META[hazard]?.label ?? hazard}
              </div>
              <div className="mt-1 font-mono text-sm text-bluette">
                {range.min.toFixed(2)} – {range.max.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </ChartCard>

      {/* Caveats */}
      <div className="space-y-2">
        <Caveat>
          This dashboard presents scenario-based estimates. Results are not
          forecasts and are not observed losses.
        </Caveat>
        <Caveat>
          The model estimates business-interruption impacts on production flows.
          It does not estimate physical damage to assets.
        </Caveat>
        {DATA_CAVEATS.map((c) => (
          <Caveat key={c}>{c}</Caveat>
        ))}
        {status && !status.runtime_matches_expected && (
          <Caveat>{status.runtime_caveat}</Caveat>
        )}
      </div>
    </div>
  );
}
