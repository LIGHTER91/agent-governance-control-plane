import { EvidenceBundleViewer } from "./evidence-bundle-viewer";

export default function EvidencePage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Evidence Review</p>
        <h2>Evidence</h2>
        <p>
          Read-only Evidence Bundle JSON from the backend API, organized by
          Agent metadata, audit logs, runs, trace events, policy decisions, and
          human approvals.
        </p>
      </section>

      <EvidenceBundleViewer />
    </>
  );
}
