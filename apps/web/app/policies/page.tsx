import { PoliciesManager } from "./policies-manager";

export default function PoliciesPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Policy Governance</p>
        <h2>Policies</h2>
        <p>
          Manage Policy lifecycle records and constrained PolicyRule condition
          fields from the backend API. PolicyRules define executable
          conditions; simulation, versioning, and review workflows stay out of
          scope.
        </p>
      </section>

      <PoliciesManager />
    </>
  );
}
