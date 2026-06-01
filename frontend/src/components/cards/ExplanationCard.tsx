import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Explanatory text card used to add narrative around charts.
 * Optional Lime left border for emphasis.
 */
export function ExplanationCard({
  title,
  children,
  emphasis = false,
  className,
}: {
  title?: string;
  children: React.ReactNode;
  emphasis?: boolean;
  className?: string;
}) {
  return (
    <Card
      className={cn(
        "p-4",
        emphasis && "border-l-4 border-l-lime",
        className,
      )}
    >
      {title && (
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-grey-text">
          {title}
        </h4>
      )}
      <div className="space-y-2 text-sm leading-relaxed text-ink">{children}</div>
    </Card>
  );
}
