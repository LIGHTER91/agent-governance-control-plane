import Link from "next/link";
import { EvidenceBundleViewer } from "./evidence-bundle-viewer";

const evidenceWorkflowCards = [
  {
    title: "Policy decisions",
    text: "Which PolicyDecision allowed, denied, or escalated the action."
  },
  {
    title: "Metadata checks",
    text: "Metadata-only CheckResults linked to the decision when available."
  },
  {
    title: "Human reviews",
    text: "HumanApproval or review evidence for actions that required oversight."
  },
  {
    title: "Audit trail",
    text: "Append-only AuditLog events included by the Evidence Bundle read model."
  },
  {
    title: "Export bundle",
    text: "Download the bounded JSON artifact returned by the backend."
  }
];

export default function EvidencePage() {
  return (
    <div className="evidence-explorer-page">
      <section className="evidence-explorer-hero" aria-labelledby="evidence-title">
        <div>
          <p className="agcp-eyebrow">Evidence review</p>
          <h1 id="evidence-title">Evidence & Audit</h1>
          <p>
            Export and inspect the evidence trail behind agent governance decisions.
          </p>
        </div>
        <div className="evidence-boundary-copy" aria-label="Evidence safety boundaries">
          <span>Evidence is generated from real AGCP records.</span>
          <span>AGCP does not certify legal compliance.</span>
          <span>Evidence bundles should not include raw prompts, source content, or secrets.</span>
          <span>No fake production simulation is shown.</span>
        </div>
      </section>

      <section className="evidence-workflow-cards" aria-label="Evidence workflow">
        {evidenceWorkflowCards.map((card) => (
          <article className="evidence-workflow-card" key={card.title}>
            <strong>{card.title}</strong>
            <p>{card.text}</p>
          </article>
        ))}
      </section>

      <section className="evidence-route-links" aria-label="Related workflows">
        <p>
          Select an agent or decision with an available Evidence Bundle. If no
          evidence exists locally yet, run <code>.\scripts\dev-demo.ps1</code>.
        </p>
        <div>
          <Link href="/runtime-gateway">View Runtime Decisions</Link>
          <Link href="/human-approvals">View Review Inbox</Link>
          <Link href="/policies">View Policy Studio</Link>
        </div>
      </section>

      <EvidenceBundleViewer />
    </div>
  );
}
