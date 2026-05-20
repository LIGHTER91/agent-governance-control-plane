import { PlaceholderPage } from "../placeholder-content";

export default function PoliciesPage() {
  return (
    <PlaceholderPage
      eyebrow="Policy Governance"
      title="Policies"
      summary="A future workspace for policies, rules, and deterministic decisions without adding a policy editor yet."
      plannedItems={[
        { label: "Policy list", status: "planned" },
        { label: "Rule conditions", status: "backend model exists" },
        { label: "Policy decision history", status: "planned" }
      ]}
    />
  );
}
