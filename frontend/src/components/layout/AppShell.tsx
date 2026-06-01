"use client";

import { ControlPanel } from "@/components/layout/ControlPanel";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { useScenario } from "@/lib/scenario-context";
import { NO_LIVE_MODEL_NOTE } from "@/lib/constants";

/**
 * Application shell: top bar, sticky scenario control bar, left navigation,
 * and the scrollable main content area.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { loading, error } = useScenario();

  return (
    <div className="flex min-h-screen flex-col bg-grey-light">
      <TopBar />

      {/* Sticky scenario controls */}
      <div className="sticky top-0 z-20 border-b border-grey-mid bg-paper/95 px-5 py-3 backdrop-blur">
        <ControlPanel />
        <p className="mt-2 text-[11px] text-grey-text">
          {NO_LIVE_MODEL_NOTE} Province and sector filters live on the Regional
          and Sectors pages.
        </p>
      </div>

      <div className="flex flex-1">
        <aside className="hidden w-56 shrink-0 border-r border-grey-mid bg-paper md:block">
          <Sidebar />
        </aside>

        <main className="min-w-0 flex-1 px-5 py-6">
          {error ? (
            <div className="rounded-card border border-grey-mid bg-paper p-6 text-sm text-ink">
              <p className="font-semibold">Could not load dashboard data.</p>
              <p className="mt-1 text-grey-text">
                Run the export scripts first:
                <code className="ml-1 rounded bg-grey-light px-1 py-0.5 font-mono text-xs">
                  python scripts/export_dashboard_data_for_frontend.py
                </code>
              </p>
            </div>
          ) : loading ? (
            <div className="p-6 text-sm text-grey-text">Loading scenarios…</div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
