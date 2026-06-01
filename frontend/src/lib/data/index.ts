/**
 * Static data adapter layer.
 *
 * All dashboard data lives as precomputed JSON under /public/data and is read
 * client-side. These functions and hooks are the ONLY place that knows file
 * paths; components consume typed results. No model runs in the browser.
 */
import useSWR from "swr";

import { DATA_BASE } from "@/lib/constants";
import type {
  CrosswalkRow,
  DataStatus,
  FlowRecord,
  ProvinceExposure,
  ProvinceFlowCell,
  ProvinceFeatureCollection,
  ProvinceMetric,
  ProvinceSectorLoss,
  ScenarioIndex,
  ScenarioSummary,
  SectorFlowCell,
  SectorLoss,
  SectorMeta,
  SectorVulnerability,
} from "@/lib/types";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`Failed to load ${path}: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

const url = (p: string) => `${DATA_BASE}/${p}`;

// ---- top-level loaders (named per the dashboard spec) ---------------------
export const loadScenarioIndex = () =>
  fetchJson<ScenarioIndex>(url("scenario_index.json"));
export const loadKpiSummary = () =>
  fetchJson<ScenarioSummary[]>(url("kpi_summary.json"));
export const loadCrosswalk = () => fetchJson<CrosswalkRow[]>(url("crosswalk.json"));
export const loadSectorMeta = () => fetchJson<SectorMeta[]>(url("sector_meta.json"));
export const loadSectorVulnerability = () =>
  fetchJson<SectorVulnerability[]>(url("sector_hazard_vulnerability.json"));
export const loadHazardExposure = () =>
  fetchJson<ProvinceExposure[]>(url("province_hazard_exposure.json"));
export const loadDataStatus = () => fetchJson<DataStatus>(url("data_status.json"));
export const loadProvinceGeoJson = () =>
  fetchJson<ProvinceFeatureCollection>(url("geographies/italy_provinces.geojson"));

// ---- per-scenario loaders -------------------------------------------------
export const loadProvinceMetrics = (scenarioId: string) =>
  fetchJson<ProvinceMetric[]>(url(`province_metrics/${scenarioId}.json`));
export const loadSectorLosses = (scenarioId: string) =>
  fetchJson<SectorLoss[]>(url(`sector_losses/${scenarioId}.json`));
export const loadProvinceSectorLosses = (scenarioId: string) =>
  fetchJson<ProvinceSectorLoss[]>(url(`province_sector_losses/${scenarioId}.json`));
export const loadTopPenalizedFlows = (scenarioId: string) =>
  fetchJson<FlowRecord[]>(url(`top_penalized_flows/${scenarioId}.json`));
export const loadTopFavoredFlows = (scenarioId: string) =>
  fetchJson<FlowRecord[]>(url(`top_favored_flows/${scenarioId}.json`));
export const loadProvinceFlowHeatmap = (scenarioId: string) =>
  fetchJson<ProvinceFlowCell[]>(url(`province_flow_heatmap/${scenarioId}.json`));
export const loadSectorFlowHeatmap = (scenarioId: string) =>
  fetchJson<SectorFlowCell[]>(url(`sector_flow_heatmap/${scenarioId}.json`));

// ---- SWR hooks (cached, deduped) -----------------------------------------
const swrOpts = { revalidateOnFocus: false, revalidateIfStale: false };

export function useScenarioIndex() {
  return useSWR("scenario_index", loadScenarioIndex, swrOpts);
}
export function useCrosswalk() {
  return useSWR("crosswalk", loadCrosswalk, swrOpts);
}
export function useSectorMeta() {
  return useSWR("sector_meta", loadSectorMeta, swrOpts);
}
export function useSectorVulnerability() {
  return useSWR("sector_vulnerability", loadSectorVulnerability, swrOpts);
}
export function useHazardExposure() {
  return useSWR("hazard_exposure", loadHazardExposure, swrOpts);
}
export function useDataStatus() {
  return useSWR("data_status", loadDataStatus, swrOpts);
}
export function useProvinceGeoJson() {
  return useSWR("province_geojson", loadProvinceGeoJson, swrOpts);
}

export function useProvinceMetrics(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["province_metrics", scenarioId] : null,
    () => loadProvinceMetrics(scenarioId as string),
    swrOpts,
  );
}
export function useSectorLosses(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["sector_losses", scenarioId] : null,
    () => loadSectorLosses(scenarioId as string),
    swrOpts,
  );
}
export function useProvinceSectorLosses(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["province_sector_losses", scenarioId] : null,
    () => loadProvinceSectorLosses(scenarioId as string),
    swrOpts,
  );
}
export function useTopPenalizedFlows(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["top_penalized_flows", scenarioId] : null,
    () => loadTopPenalizedFlows(scenarioId as string),
    swrOpts,
  );
}
export function useTopFavoredFlows(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["top_favored_flows", scenarioId] : null,
    () => loadTopFavoredFlows(scenarioId as string),
    swrOpts,
  );
}
export function useProvinceFlowHeatmap(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["province_flow_heatmap", scenarioId] : null,
    () => loadProvinceFlowHeatmap(scenarioId as string),
    swrOpts,
  );
}
export function useSectorFlowHeatmap(scenarioId: string | undefined) {
  return useSWR(
    scenarioId ? ["sector_flow_heatmap", scenarioId] : null,
    () => loadSectorFlowHeatmap(scenarioId as string),
    swrOpts,
  );
}
