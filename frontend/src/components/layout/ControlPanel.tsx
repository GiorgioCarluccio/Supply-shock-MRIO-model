"use client";

import { useMemo } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCrosswalk, useSectorMeta } from "@/lib/data";
import { HAZARD_META, SEVERITY_LABELS, sectorLabel } from "@/lib/constants";
import { useScenario } from "@/lib/scenario-context";

/**
 * Shared scenario controls: hazard, scenario/severity, province, sector.
 * Province and sector default to "All" and are optional context filters.
 * Renders inline so it can live in the sticky top control bar.
 */
export function ControlPanel({
  showHazard = true,
  showScenario = true,
  showProvince = false,
  showSector = false,
}: {
  showHazard?: boolean;
  showScenario?: boolean;
  showProvince?: boolean;
  showSector?: boolean;
}) {
  const {
    hazards,
    hazard,
    setHazard,
    scenariosForHazard,
    scenarioId,
    setScenarioId,
    regionCode,
    setRegionCode,
    sectorCode,
    setSectorCode,
  } = useScenario();
  const { data: crosswalk } = useCrosswalk();
  const { data: sectors } = useSectorMeta();

  const provinces = useMemo(
    () =>
      (crosswalk ?? [])
        .slice()
        .sort((a, b) => a.province_name.localeCompare(b.province_name)),
    [crosswalk],
  );

  return (
    <div className="flex flex-wrap items-end gap-x-4 gap-y-2">
      {showHazard && (
        <Field label="Hazard">
          <Select value={hazard} onValueChange={setHazard}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {hazards.map((h) => (
                <SelectItem key={h} value={h}>
                  {HAZARD_META[h]?.label ?? h}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}

      {showScenario && (
        <Field label="Scenario / severity">
          <Select value={scenarioId} onValueChange={setScenarioId}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {scenariosForHazard.map((s) => (
                <SelectItem key={s.scenario_id} value={s.scenario_id}>
                  {SEVERITY_LABELS[s.severity] ?? s.severity}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}

      {showProvince && (
        <Field label="Province">
          <Select
            value={regionCode ?? "__all__"}
            onValueChange={(v) => setRegionCode(v === "__all__" ? null : v)}
          >
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All provinces</SelectItem>
              {provinces.map((p) => (
                <SelectItem key={p.region_code} value={p.region_code}>
                  {p.province_name} ({p.province_abbr})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      )}

      {showSector && (
        <Field label="Sector">
          <Select
            value={sectorCode ?? "__all__"}
            onValueChange={(v) => setSectorCode(v === "__all__" ? null : v)}
          >
            <SelectTrigger className="w-64">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All sectors</SelectItem>
              {(sectors ?? [])
                .slice()
                .sort((a, b) => a.sector_code.localeCompare(b.sector_code))
                .map((s) => (
                  <SelectItem key={s.sector_code} value={s.sector_code}>
                    {sectorLabel(s.sector_code, s.macrosector_code)}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </Field>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-medium uppercase tracking-wide text-grey-text">
        {label}
      </span>
      {children}
    </label>
  );
}
