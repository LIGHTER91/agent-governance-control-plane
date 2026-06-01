import { EvidenceBundleViewer } from "./evidence-bundle-viewer";

export default function EvidencePage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Evidence Review</p>
        <h2>Evidence</h2>
        <p>
          Manual Evidence Bundle review and JSON download for one Agent. The
          page explains the evidence chain while keeping the bounded backend
          JSON as the canonical audit artifact.
        </p>
      </section>

      <EvidenceBundleViewer />
    </>
  );
}
