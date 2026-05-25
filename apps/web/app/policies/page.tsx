import { PoliciesManager } from "./policies-manager";

export default function PoliciesPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Policy Governance</p>
        <h2>Policies</h2>
        <p>
          Manage Policy lifecycle records from the backend API. PolicyRules
          define executable conditions; this view keeps rule editing,
          simulation, and versioning out of scope.
        </p>
      </section>

      <PoliciesManager />
    </>
  );
}
