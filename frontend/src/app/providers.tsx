"use client";

import { ScenarioProvider } from "@/lib/scenario-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return <ScenarioProvider>{children}</ScenarioProvider>;
}
