import type { HTMLAttributes, ReactNode } from "react";

type Tone =
  | "default"
  | "ok"
  | "warn"
  | "danger"
  | "info"
  | "purple"
  | "muted";

export function AGCPPanel({
  children,
  className = "",
  ...props
}: {
  children: ReactNode;
  className?: string;
} & HTMLAttributes<HTMLElement>) {
  return (
    <section className={`agcp-panel ${className}`} {...props}>
      {children}
    </section>
  );
}

export function AGCPSectionHeader({
  eyebrow,
  title,
  description,
  meta,
  actions
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="agcp-section-header">
      <div>
        {eyebrow ? <span className="agcp-eyebrow">{eyebrow}</span> : null}
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
      </div>
      {meta || actions ? (
        <div className="agcp-section-actions">
          {meta}
          {actions}
        </div>
      ) : null}
    </header>
  );
}

export function AGCPBadge({
  children,
  tone = "default"
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return <span className={`agcp-badge ${tone}`}>{children}</span>;
}

export function AGCPEmptyState({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="agcp-state">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}

export function AGCPErrorState({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="agcp-state error" role="alert">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}

export function AGCPDataTable({
  children,
  className = ""
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`agcp-table-wrap ${className}`}>
      <table className="agcp-data-table">{children}</table>
    </div>
  );
}

export function AGCPMetaGrid({
  items
}: {
  items: Array<{ label: string; value: ReactNode; tone?: Tone }>;
}) {
  return (
    <dl className="agcp-meta-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd className={item.tone ? `tone-${item.tone}` : undefined}>
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function AGCPTimelineItem({
  badge,
  tone = "info",
  title,
  timestamp,
  children
}: {
  badge: ReactNode;
  tone?: Tone;
  title: string;
  timestamp?: ReactNode;
  children: ReactNode;
}) {
  return (
    <li className="agcp-timeline-item">
      <div className="agcp-timeline-marker" />
      <div className="agcp-timeline-card">
        <div className="agcp-timeline-head">
          <AGCPBadge tone={tone}>{badge}</AGCPBadge>
          {timestamp ? <time>{timestamp}</time> : null}
        </div>
        <strong>{title}</strong>
        <div className="agcp-timeline-body">{children}</div>
      </div>
    </li>
  );
}
