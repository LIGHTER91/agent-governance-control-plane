import { RuntimeActivityList } from "./runtime-activity-list";

export default function RuntimeGatewayPage() {
  return (
    <div className="runtime-decisions-page">
      <section className="runtime-decisions-hero" aria-labelledby="runtime-decisions-title">
        <div>
          <p className="agcp-eyebrow">Runtime Gateway</p>
          <h1 id="runtime-decisions-title">Runtime Decisions</h1>
          <p>
            Trace how AGCP evaluated agent actions, metadata checks, policy decisions, reviews,
            and evidence. AGCP records and governs decisions; the caller or orchestrator remains
            responsible for honoring proceed=false and for executing or stopping the tool.
          </p>
        </div>
        <div className="runtime-decisions-boundary" aria-label="Runtime boundary">
          <span>decision evidence</span>
          <span>metadata-only checks</span>
          <span>not executing the tool</span>
          <span>no fake production simulation</span>
        </div>
      </section>

      <RuntimeActivityList />

      <section className="runtime-demo-callout" aria-labelledby="runtime-demo-title">
        <div>
          <p className="agcp-eyebrow">Local demo</p>
          <h2 id="runtime-demo-title">Run a local metadata pre-check decision</h2>
          <p>
            Use the one-command demo to seed a safe local scenario, call the Runtime Gateway, and
            produce real metadata-only CheckResults, a PolicyDecision, and a HumanApproval when the
            active policy requires review.
          </p>
        </div>
        <code>.\scripts\dev-demo.ps1</code>
      </section>
    </div>
  );
}
