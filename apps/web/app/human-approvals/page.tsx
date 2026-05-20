import { PlaceholderPage } from "../placeholder-content";

export default function HumanApprovalsPage() {
  return (
    <PlaceholderPage
      eyebrow="Human Oversight"
      title="Human Approvals"
      summary="A future reviewer queue for pending approvals and audited review outcomes."
      plannedItems={[
        { label: "Pending approvals", status: "planned" },
        { label: "Approve and reject actions", status: "backend exists" },
        { label: "Review history", status: "planned" }
      ]}
    />
  );
}
