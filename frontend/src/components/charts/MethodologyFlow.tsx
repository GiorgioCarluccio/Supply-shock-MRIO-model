"use client";

import { ArrowRight } from "lucide-react";

import { cn } from "@/lib/utils";

export interface FlowStep {
  title: string;
  detail?: string;
  accent?: boolean;
}

/**
 * Horizontal pipeline diagram built from React cards connected with arrows.
 * Wraps responsively; arrows rotate down between rows on small screens.
 */
export function MethodologyFlow({ steps }: { steps: FlowStep[] }) {
  return (
    <div className="flex flex-wrap items-stretch gap-2">
      {steps.map((step, i) => (
        <div key={step.title} className="flex items-stretch gap-2">
          <div
            className={cn(
              "flex w-44 flex-col justify-center rounded-card border px-3 py-3",
              step.accent
                ? "border-bluette bg-bluette text-paper"
                : "border-grey-mid bg-grey-light text-ink",
            )}
          >
            <span className="text-xs font-semibold leading-tight">
              {step.title}
            </span>
            {step.detail && (
              <span
                className={cn(
                  "mt-1 text-[11px] leading-snug",
                  step.accent ? "text-paper/80" : "text-grey-text",
                )}
              >
                {step.detail}
              </span>
            )}
          </div>
          {i < steps.length - 1 && (
            <div className="flex items-center">
              <ArrowRight className="h-4 w-4 shrink-0 text-grey-text" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
