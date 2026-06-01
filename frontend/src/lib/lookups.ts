"use client";

import { useMemo } from "react";

import { useCrosswalk, useSectorMeta } from "@/lib/data";
import { MACROSECTOR_LABELS } from "@/lib/constants";

export interface RegionLabels {
  /** NUTS region_code -> full province name (falls back to the code). */
  name: (regionCode: string) => string;
  /** NUTS region_code -> two-letter plate abbreviation (falls back to code). */
  abbr: (regionCode: string) => string;
  /** "Name (AB)" combined label. */
  full: (regionCode: string) => string;
  ready: boolean;
}

/**
 * Resolve model NUTS region_codes (e.g. ITC11) to human province names /
 * abbreviations via the crosswalk, so the UI never surfaces raw codes.
 */
export function useRegionLabels(): RegionLabels {
  const { data: crosswalk } = useCrosswalk();
  return useMemo(() => {
    const byRegion = new Map(
      (crosswalk ?? []).map((r) => [
        r.region_code,
        { name: r.province_name, abbr: r.province_abbr },
      ]),
    );
    return {
      name: (rc) => byRegion.get(rc)?.name ?? rc,
      abbr: (rc) => byRegion.get(rc)?.abbr ?? rc,
      full: (rc) => {
        const m = byRegion.get(rc);
        return m ? `${m.name} (${m.abbr})` : rc;
      },
      ready: byRegion.size > 0,
    };
  }, [crosswalk]);
}

export interface SectorLabels {
  /** sector_code -> "C20 · Manufacturing" style label. */
  full: (sectorCode: string) => string;
  /** sector_code -> macrosector name only. */
  macro: (sectorCode: string) => string;
}

/** Resolve NACE sector codes to a label enriched with the macrosector name. */
export function useSectorLabels(): SectorLabels {
  const { data: sectors } = useSectorMeta();
  return useMemo(() => {
    const byCode = new Map(
      (sectors ?? []).map((s) => [s.sector_code, s.macrosector_code]),
    );
    const macroName = (code: string) => {
      const macro = byCode.get(code);
      return macro ? MACROSECTOR_LABELS[macro] ?? macro : "";
    };
    return {
      full: (code) => {
        const m = macroName(code);
        return m ? `${code} · ${m}` : code;
      },
      macro: macroName,
    };
  }, [sectors]);
}
