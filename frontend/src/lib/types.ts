/**
 * TypeScript types for the static dashboard data contract.
 * Field names mirror the JSON produced by
 * scripts/export_dashboard_data_for_frontend.py. Keep this file as the single
 * source of truth for column names so components never hardcode them.
 */

export type HazardId = "heatwave" | "flood" | "landslide";

export interface ScenarioSummary {
  scenario_id: string;
  hazard: string;
  severity: string;
  base_interruption_days: number;
  scenario_intensity_multiplier: number;
  demand_pass_through_lambda: number;
  max_supply_shock: number;
  max_demand_shock: number;
  n_nodes: number;
  n_nodes_shocked: number;
  mean_supply_shock: number;
  max_supply_shock_applied: number;
  mean_demand_shock: number;
  max_demand_shock_applied: number;
  converged: boolean;
  iterations: number;
  total_direct_loss: number;
  total_indirect_loss: number;
  total_loss: number;
  total_x_pre: number;
  total_x_post: number;
  loss_rate_total: number;
  total_over_direct_multiplier: number;
}

export interface ScenarioIndex {
  n_scenarios: number;
  scenarios: string[];
  generated_files: string[];
  note: string;
  summaries: ScenarioSummary[];
  hazards: { hazard: string; scenarios: { scenario_id: string; severity: string }[] }[];
  expected_runtime: { max_iter: number; gamma: number };
  runtime_matches_expected: boolean;
  runtime_caveat: string | null;
}

/** Per-province merged metrics — primary source for the map & regional panel. */
export interface ProvinceMetric {
  scenario_id: string;
  region_code: string;
  province_code: number | null;
  province_name: string | null;
  province_abbr: string | null;
  n_nodes: number;
  x_pre: number;
  x_post: number;
  direct_loss: number;
  indirect_loss: number;
  total_loss: number;
  loss_rate: number;
  indirect_exposure_ratio: number;
  mean_supply_shock: number;
  max_supply_shock: number;
  mean_demand_shock: number | null;
  max_demand_shock: number | null;
  raw_exposure: number | null;
  exposure_weight: number | null;
  equivalent_stop_days: number | null;
  base_interruption_days: number | null;
}

export interface SectorLoss {
  scenario_id: string;
  sector_code: string;
  macrosector_code: string;
  n_nodes: number;
  x_pre: number;
  x_post: number;
  direct_loss: number;
  indirect_loss: number;
  total_loss: number;
  mean_supply_shock: number;
  max_supply_shock: number;
  loss_rate: number;
}

export interface ProvinceSectorLoss {
  scenario_id: string;
  node_id: number;
  region_code: string;
  province_code: number;
  sector_code: string;
  macrosector_code: string;
  x_pre: number;
  x_post: number;
  direct_loss: number;
  indirect_loss: number;
  total_loss: number;
  loss_rate: number;
  supply_shock: number;
  demand_shock: number;
}

export interface FlowRecord {
  scenario_id: string;
  origin_node_id: number;
  origin_region: string;
  origin_sector: string;
  destination_node_id: number;
  destination_region: string;
  destination_sector: string;
  delta_value: number;
  relative_change: number;
  pre_value: number;
  post_value: number;
}

export interface ProvinceFlowCell {
  scenario_id: string;
  origin_region_code: string;
  destination_region_code: string;
  pre_value: number;
  post_value: number;
  delta_value: number;
}

export interface SectorFlowCell {
  scenario_id: string;
  origin_sector_code: string;
  destination_sector_code: string;
  pre_value: number;
  post_value: number;
  delta_value: number;
}

export interface ProvinceExposure {
  province_code: number;
  province_name: string;
  province_abbr: string;
  hazard: string;
  severity: string;
  raw_exposure: number;
  exposure_weight: number;
  exposure_type: string;
  source_file: string;
  source_column: string;
  method: string;
}

export interface CrosswalkRow {
  province_code: number;
  province_name: string;
  province_abbr: string;
  region_code: string;
}

export interface SectorMeta {
  sector_group_id: number;
  sector_code: string;
  macrosector_code: string;
  /** Full NACE sector name from the decoder; absent if the decoder was missing. */
  sector_name?: string;
}

export interface SectorVulnerability {
  sector_code: string;
  macrosector_code: string;
  hazard: string;
  sector_vulnerability: number;
  rationale: string;
}

export interface DataStatus {
  climate_exposure: string;
  shock_calibration: string;
  sam_model_inputs: string;
  simulation_outputs: string;
  frontend_mode: string;
  geojson_present: boolean;
  n_scenarios: number;
  iterations_in_outputs: number[];
  expected_max_iter: number;
  expected_gamma: number;
  runtime_matches_expected: boolean;
  runtime_caveat: string | null;
}

export interface ProvinceFeatureProps {
  province_code: number;
  province_name: string;
  province_abbr: string;
  region_code: string;
}

export interface ProvinceFeature {
  type: "Feature";
  properties: ProvinceFeatureProps;
  geometry: { type: string; coordinates: unknown };
}

export interface ProvinceFeatureCollection {
  type: "FeatureCollection";
  features: ProvinceFeature[];
}

export type MapMetric =
  | "raw_exposure"
  | "mean_supply_shock"
  | "total_loss"
  | "loss_rate";
