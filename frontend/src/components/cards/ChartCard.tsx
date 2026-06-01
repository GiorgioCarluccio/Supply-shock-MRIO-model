import {
  Card,
  CardContent,
  CardHeader,
  CardNote,
  CardSubtitle,
  CardTitle,
} from "@/components/ui/card";

/**
 * Standard frame for a chart: title (what it shows), optional subtitle
 * (key framing), the chart body, and an optional source/note line.
 * Encodes the brand title/label hierarchy.
 */
export function ChartCard({
  title,
  subtitle,
  note,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  note?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            {subtitle && <CardSubtitle>{subtitle}</CardSubtitle>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      </CardHeader>
      <CardContent>
        {children}
        {note && <CardNote>{note}</CardNote>}
      </CardContent>
    </Card>
  );
}
