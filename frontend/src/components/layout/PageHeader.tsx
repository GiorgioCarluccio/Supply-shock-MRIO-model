/** Large section title with a short explanatory intro. */
export function PageHeader({
  title,
  intro,
}: {
  title: string;
  intro?: React.ReactNode;
}) {
  return (
    <div className="mb-5">
      <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
      {intro && (
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-grey-text">
          {intro}
        </p>
      )}
    </div>
  );
}
