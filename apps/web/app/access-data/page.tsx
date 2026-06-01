import { SourcesWorkflow } from "./sources-workflow";

export default function AccessDataPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Access & Data</p>
        <h2>Source Data Usage Profiles</h2>
        <p>
          Review Source governance metadata for contextual runtime decisions:
          classification, allowed purposes, prohibited processing, review
          status, DPIA references, and safe metadata. These profiles are evidence
          inputs and do not certify legal compliance.
        </p>
      </section>

      <SourcesWorkflow />
    </>
  );
}
