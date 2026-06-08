import { HumanApprovalsList } from "./human-approvals-list";

export default function HumanApprovalsPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Human Oversight</p>
        <h2>Human Approvals</h2>
        <p>
          Review HumanApproval records from the backend API as a governance
          queue. This page keeps reviewer, requester, policy decision, status,
          and timestamp context visible without inventing approval records.
        </p>
      </section>

      <HumanApprovalsList />
    </>
  );
}
