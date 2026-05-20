const statusItems = [
  {
    title: "Agent Registry",
    label: "Backend ready",
    tone: "done",
    body: "Agents can be registered with ownership, environment, status, and risk metadata through the backend API."
  },
  {
    title: "Runtime Gateway",
    label: "Foundation",
    tone: "foundation",
    body: "Simulation and config-gated enforcement paths can return governed tool-call decisions. Wrappers still enforce proceed locally."
  },
  {
    title: "Human Approval",
    label: "Backend ready",
    tone: "done",
    body: "Policy decisions can create pending approvals, and review transitions are audited with minimal role checks."
  },
  {
    title: "Evidence Bundle",
    label: "Backend ready",
    tone: "done",
    body: "Agent evidence can be exported as filtered JSON for authorized auditor or platform admin actors."
  },
  {
    title: "RBAC Foundations",
    label: "Limited",
    tone: "limited",
    body: "ActorContext, service API keys, scopes, and minimal local RBAC exist. Full user auth and team membership are not implemented."
  }
];

const nextWork = [
  {
    title: "Agent list page",
    body: "Connect the shell to the Agent Registry API once the dashboard data access pattern is chosen."
  },
  {
    title: "Human approvals page",
    body: "Expose pending review work without adding notifications or workflow automation."
  },
  {
    title: "Evidence page",
    body: "Add a safe JSON evidence viewer after authorization behavior is settled."
  },
  {
    title: "Owner-based access checks",
    body: "Move beyond broad local roles once ownership and team resolution are designed."
  }
];

export default function HomePage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Current backend state</p>
        <h2>V0 governance flow is implemented; product UI is just starting.</h2>
        <p>
          This shell reflects the current Agent Governance Control Plane
          foundation: registry, deterministic runtime decisions, human
          oversight, audited evidence, and early authorization boundaries. It is
          not a production readiness claim.
        </p>
      </section>

      <section className="status-band" aria-label="V0 capability overview">
        <div className="status-grid">
          {statusItems.map((item) => (
            <article className="status-card" key={item.title}>
              <span className={`status-label ${item.tone}`}>{item.label}</span>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <h3 className="section-title">Next dashboard work</h3>
      <section className="work-grid" aria-label="Next dashboard work">
        {nextWork.map((item) => (
          <article className="work-item" key={item.title}>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
          </article>
        ))}
      </section>
    </>
  );
}
