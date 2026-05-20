type PlaceholderPageProps = {
  title: string;
  eyebrow: string;
  summary: string;
  plannedItems: Array<{
    label: string;
    status: string;
  }>;
};

export function PlaceholderPage({
  title,
  eyebrow,
  summary,
  plannedItems
}: PlaceholderPageProps) {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p>{summary}</p>
      </section>

      <section className="placeholder-panel">
        <p>
          This area is reserved for the product workflow. It does not call the
          backend yet and does not display synthetic operational data.
        </p>
        <ul className="placeholder-list">
          {plannedItems.map((item) => (
            <li key={item.label}>
              {item.label}
              <span>{item.status}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
