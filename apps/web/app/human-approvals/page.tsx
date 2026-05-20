import { HumanApprovalsList } from "./human-approvals-list";

export default function HumanApprovalsPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Human Oversight</p>
        <h2>Human Approvals</h2>
        <p>
          Read-only approval records from the backend API, shown with requester
          and reviewer actor fields, status, policy decision linkage, and review
          timestamps.
        </p>
      </section>

      <HumanApprovalsList />
    </>
  );
}
