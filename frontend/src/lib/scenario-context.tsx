"use client";

/**
 * Shared selection state for the dashboard controls:
 * hazard, scenario/severity, province (NUTS region_code), and sector.
 * Persisted across pages so the user's context follows them through the nav.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useScenarioIndex } from "@/lib/data";
import type { ScenarioSummary } from "@/lib/types";

interface ScenarioState {
  loading: boolean;
  error: unknown;
  /** all scenario summaries from the index */
  summaries: ScenarioSummary[];
  hazards: string[];
  hazard: string;
  scenarioId: string;
  /** scenarios available for the selected hazard */
  scenariosForHazard: ScenarioSummary[];
  selected: ScenarioSummary | undefined;
  /** selected province NUTS region_code, or null for "all provinces" */
  regionCode: string | null;
  /** selected sector code, or null */
  sectorCode: string | null;
  setHazard: (h: string) => void;
  setScenarioId: (id: string) => void;
  setRegionCode: (rc: string | null) => void;
  setSectorCode: (s: string | null) => void;
}

const Ctx = createContext<ScenarioState | null>(null);

export function ScenarioProvider({ children }: { children: React.ReactNode }) {
  const { data: index, error, isLoading } = useScenarioIndex();
  const [hazard, setHazardState] = useState<string>("flood");
  const [scenarioId, setScenarioId] = useState<string>("");
  const [regionCode, setRegionCode] = useState<string | null>(null);
  const [sectorCode, setSectorCode] = useState<string | null>(null);

  const summaries = useMemo(() => index?.summaries ?? [], [index]);
  const hazards = useMemo(
    () => Array.from(new Set(summaries.map((s) => s.hazard))),
    [summaries],
  );

  // Initialise defaults once the index is loaded.
  useEffect(() => {
    if (!summaries.length) return;
    const validHazard = hazards.includes(hazard) ? hazard : hazards[0];
    if (validHazard !== hazard) setHazardState(validHazard);
    const forHazard = summaries.filter((s) => s.hazard === validHazard);
    if (!forHazard.some((s) => s.scenario_id === scenarioId)) {
      setScenarioId(forHazard[0]?.scenario_id ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summaries, hazards]);

  const setHazard = useCallback(
    (h: string) => {
      setHazardState(h);
      const forHazard = summaries.filter((s) => s.hazard === h);
      setScenarioId(forHazard[0]?.scenario_id ?? "");
    },
    [summaries],
  );

  const scenariosForHazard = useMemo(
    () => summaries.filter((s) => s.hazard === hazard),
    [summaries, hazard],
  );
  const selected = useMemo(
    () => summaries.find((s) => s.scenario_id === scenarioId),
    [summaries, scenarioId],
  );

  const value: ScenarioState = {
    loading: isLoading,
    error,
    summaries,
    hazards,
    hazard,
    scenarioId,
    scenariosForHazard,
    selected,
    regionCode,
    sectorCode,
    setHazard,
    setScenarioId,
    setRegionCode,
    setSectorCode,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useScenario(): ScenarioState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useScenario must be used within ScenarioProvider");
  return ctx;
}
