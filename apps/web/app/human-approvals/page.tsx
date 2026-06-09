import { HumanApprovalsList } from "./human-approvals-list";
import { PolicyReviewsList } from "./policy-reviews-list";

export default function HumanApprovalsPage() {
  return (
    <>
      <section className="page-header">
        <p className="eyebrow">Human Oversight</p>
        <h2>Human Approvals</h2>
        <p>
          Review HumanApproval records from the backend API as a governance
          queue. This page also shows PolicyVersion review requests for draft
          policy snapshots. Review approval does not activate runtime policy
          versions.
        </p>
      </section>

      <PolicyReviewsList />
      <HumanApprovalsList />
    </>
  );
}
