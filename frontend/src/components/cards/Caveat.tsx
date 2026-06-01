import { Info } from "lucide-react";

import { cn } from "@/lib/utils";

/** Inline caveat / methodology note. Bluette-tinted, low-noise. */
export function Caveat({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-card border border-grey-mid bg-paper px-3 py-2 text-[12px] leading-snug text-grey-text",
        className,
      )}
    >
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-bluette" />
      <span>{children}</span>
    </div>
  );
}
