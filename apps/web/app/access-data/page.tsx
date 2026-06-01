import { AccessGrantsWorkflow } from "./access-grants-workflow";
import { SourcesWorkflow } from "./sources-workflow";

export default function AccessDataPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Access & Data</p>
        <h2>Access Grants and Source Data Usage</h2>
        <p>
          Review declared Agent access and Source governance metadata for
          contextual runtime decisions. Access Grants are governance records,
          and Data Usage Profiles are evidence inputs; neither certifies legal
          compliance or automatically enforces runtime access.
        </p>
      </section>

      <AccessGrantsWorkflow />
      <SourcesWorkflow />
    </>
  );
}
