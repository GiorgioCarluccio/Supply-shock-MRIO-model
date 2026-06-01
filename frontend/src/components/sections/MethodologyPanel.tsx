"use client";

import { MethodologyFlow } from "@/components/charts/MethodologyFlow";
import { Caveat } from "@/components/cards/Caveat";
import { ChartCard } from "@/components/cards/ChartCard";
import { ExplanationCard } from "@/components/cards/ExplanationCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { useDataStatus } from "@/lib/data";

export function MethodologyPanel() {
  const { data: status } = useDataStatus();

  return (
    <div className="space-y-5">
      <PageHeader
        title="Methodology"
        intro="How physical hazard exposure becomes an estimate of business-interruption losses propagated through the provincial input-output economy."
      />

      <ChartCard
        title="Modelling pipeline"
        subtitle="From climate hazard data to dashboard outputs"
      >
        <MethodologyFlow
          steps={[
            { title: "Climate hazard data", detail: "E-OBS, PIR, ISPRA inputs" },
            { title: "Provincial exposure", detail: "exposure indicators per province" },
            { title: "Shock calibration", detail: "supply & demand shocks", accent: true },
            { title: "SAM / IO propagation", detail: "provincial economic network", accent: true },
            { title: "Direct & indirect losses", detail: "production interruption" },
            { title: "Flow reconfiguration", detail: "penalised / favoured flows" },
            { title: "Dashboard outputs", detail: "precomputed scenarios" },
          ]}
        />
      </ChartCard>

      <ChartCard
        title="Exposure → shock transformation"
        subtitle="How a physical exposure indicator becomes an economic shock"
      >
        <MethodologyFlow
          steps={[
            { title: "Exposure", detail: "hazard exposure weight" },
            { title: "× interruption days", detail: "hazard base duration" },
            { title: "× sector vulnerability", detail: "sector sensitivity factor" },
            { title: "= equivalent stop days", detail: "÷ working days", accent: true },
            { title: "→ supply shock", detail: "output not produced" },
            { title: "→ demand shock", detail: "λ pass-through" },
          ]}
        />
      </ChartCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ExplanationCard title="Direct impact" emphasis>
          <p>
            Direct losses occur at the nodes that are physically exposed to the
            hazard. The calibrated supply shock reduces a province-sector&apos;s
            achievable output in proportion to its equivalent stop days, capped
            at a maximum supply shock.
          </p>
        </ExplanationCard>
        <ExplanationCard title="Indirect impact" emphasis>
          <p>
            Indirect losses are transmitted through input-output dependencies:
            when a supplier cannot deliver, its customers&apos; production is
            constrained, and reduced incomes feed back as lower demand. These
            second-round effects typically dominate the total.
          </p>
        </ExplanationCard>
      </div>

      <ChartCard
        title="Propagation parameters — gamma and iterations"
        subtitle="How the IO solver advances the shock through the network"
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-card border border-grey-mid bg-grey-light p-4 text-sm">
            <p className="font-mono text-lg font-semibold text-bluette">γ = 0.5</p>
            <p className="mt-1 text-grey-text">
              The gamma damping factor controls how strongly each propagation
              step adjusts flows toward the new equilibrium. A value of 0.5
              applies half-step relaxation, stabilising the iteration.
            </p>
          </div>
          <div className="rounded-card border border-grey-mid bg-grey-light p-4 text-sm">
            <p className="font-mono text-lg font-semibold text-bluette">
              max_iter = 1
            </p>
            <p className="mt-1 text-grey-text">
              The dashboard specification calls for a single propagation
              iteration, giving a first-order transmission estimate. The stored
              scenario outputs should be verified against the build report.
            </p>
          </div>
        </div>
      </ChartCard>

      <Caveat>
        Dashboard uses precomputed static scenarios. Scenarios shown here are
        specified to use <strong>max_iter = 1</strong> and{" "}
        <strong>gamma = 0.5</strong>. Results are demonstrative and should not
        be interpreted as asset-damage estimates.
      </Caveat>

      {status && !status.runtime_matches_expected && (
        <Caveat>{status.runtime_caveat}</Caveat>
      )}
    </div>
  );
}
