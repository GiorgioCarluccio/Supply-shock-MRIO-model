import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Headline KPI card: large value, label, optional sublabel.
 * `accent` switches to a Bluette-filled card for the primary metric.
 */
export function KpiCard({
  label,
  value,
  sublabel,
  accent = false,
  className,
}: {
  label: string;
  value: string;
  sublabel?: string;
  accent?: boolean;
  className?: string;
}) {
  return (
    <Card
      className={cn(
        "flex flex-col justify-between p-4",
        accent && "border-bluette bg-bluette text-paper",
        className,
      )}
    >
      <span
        className={cn(
          "text-[11px] font-medium uppercase tracking-wide",
          accent ? "text-paper/75" : "text-grey-text",
        )}
      >
        {label}
      </span>
      <span className="mt-2 font-mono text-2xl font-semibold leading-none">
        {value}
      </span>
      {sublabel && (
        <span
          className={cn(
            "mt-1.5 text-xs",
            accent ? "text-paper/80" : "text-grey-text",
          )}
        >
          {sublabel}
        </span>
      )}
    </Card>
  );
}
