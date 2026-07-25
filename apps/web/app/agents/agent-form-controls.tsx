import type { ReactNode } from "react";

export function AgentStepHeader({
  id,
  step,
  title,
  description
}: {
  id?: string;
  step: string;
  title: string;
  description: string;
}) {
  return (
    <header className="agent-step-header">
      <span>{step}</span>
      <h2 id={id}>{title}</h2>
      <p>{description}</p>
    </header>
  );
}

export function AgentField({
  children,
  error,
  help,
  htmlFor,
  label,
  optional = false
}: {
  children: ReactNode;
  error?: string;
  help?: string;
  htmlFor: string;
  label: string;
  optional?: boolean;
}) {
  return (
    <div className={`agent-field ${error ? "has-error" : ""}`}>
      <label htmlFor={htmlFor}>
        <span>{label}</span>
        {optional ? <em>Optional</em> : null}
      </label>
      {children}
      {help ? <small>{help}</small> : null}
      {error ? (
        <p className="agent-field-error" id={`${htmlFor}-error`} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function AgentBoundaryNote({
  children,
  title,
  tone = "purple"
}: {
  children: ReactNode;
  title: string;
  tone?: "purple" | "warning" | "danger";
}) {
  return (
    <aside className={`agent-boundary-note ${tone}`}>
      <strong>{title}</strong>
      <p>{children}</p>
    </aside>
  );
}

export function AgentStatusBadge({ value }: { value: string }) {
  return (
    <span className={`agent-status-badge status-${value}`}>
      {value
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ")}
    </span>
  );
}
