# Policy Versioning And Review Guardrails Design

## Status

Initial backend foundation implemented. AGCP now has a minimal `PolicyVersion`
aggregate snapshot table, lifecycle APIs, and append-only audit events for
review and activation guardrails. Frontend UI, Runtime Gateway behavior, and
policy evaluator behavior are unchanged.

AGCP remains a governance and evidence control plane. It is not an
orchestrator, workflow engine, enterprise GRC suite, policy simulation engine,
or legal compliance certification system.

## Critical Assessment

Policy and PolicyRule editing is now materially riskier than it was in the
early V0 policy model. PolicyRules can match contextual runtime fields,
resolved inventory facts, and safe `check_*` CheckResult outcome summaries.
PolicyCheckSteps can also declare evidence that Runtime Gateway may collect
behind an explicit feature flag. These are useful governance capabilities, but
they mean an edit to a rule or check declaration can affect future Runtime
Gateway decisions for production Agents.

Direct active edits are risky because a small condition change can silently
broaden an allow rule, suppress a human-review escalation, make a deny rule
miss, or point check evidence at the wrong target. A well-intentioned operator
could also update a rule for a test case and accidentally change behavior for
all production Agents. Without versioning, review, and activation history,
auditors cannot easily answer which exact rule version produced a
PolicyDecision, who reviewed the change, when it became active, or how to roll
back safely.

AGCP should not overbuild enterprise change management in V1. Full separation
of duties, complex approval chains, release calendars, evidence attestations,
legal sign-off, and enterprise GRC synchronization depend on real identity,
roles, teams, and operational process that AGCP does not have yet. V1 should be
lightweight: immutable activated versions, draft-next-version editing,
review/approval state, activation and rollback semantics, and append-only audit
events.

This differs from full enterprise GRC workflows. The goal is not to certify
that a policy is legally correct or production-ready. The goal is to make
policy changes reviewable, reversible, and attributable before broader policy
authoring UI expands.

## Problem Statement

Current Policy, PolicyRule, and PolicyCheckStep records can be updated in place.
That is convenient for early development but unsafe for governed production
use. AGCP needs a small versioning and review model so active runtime policy
behavior is not changed casually.

The model should answer:

- Which Policy and PolicyRule version was active for a decision?
- Who created or edited the draft?
- What changed?
- Who reviewed or approved it?
- When was it activated?
- What version did it supersede?
- How can an operator roll back to a known approved version?

## Objects Affected

### Policy

Policy versioning should capture lifecycle metadata for the policy container:
name, description, status, review state, and the set of rule versions intended
to activate together.

### PolicyRule

PolicyRule versioning is the highest priority because rule conditions directly
influence `allow`, `deny`, `require_human_review`, or `not_applicable`
decisions. Rule condition changes should produce a new draft version rather
than mutating an active version in place.

### PolicyCheckStep

PolicyCheckStep versioning is important because check declarations affect what
evidence is collected and which CheckResults may become explicit policy
context. A step change should be reviewed with the related rule version.

### CheckTool Status

CheckTool status changes can affect check execution availability, but they are
closer to platform administration than policy authoring. V1 can keep CheckTool
status audit-only and revisit versioning once external check adapters exist.

## Minimal Lifecycle

Recommended V1 version lifecycle:

- `draft`: editable candidate version;
- `under_review`: submitted for review and no longer casually edited;
- `approved`: reviewed and eligible for activation;
- `active`: currently used by Runtime Gateway policy evaluation;
- `disabled`: intentionally unavailable for runtime evaluation;
- `archived`: retained for history and possible rollback reference.

Existing Policy statuses can continue to exist while version records introduce
review state. A migration path can later collapse or align these states if the
implementation proves simpler, but the design should distinguish:

- the lifecycle of the logical Policy record;
- the lifecycle of a specific version of policy/rule/check-step content.

## Versioning Model

Recommended V1 records:

- `PolicyVersion`;
- `PolicyRuleVersion`;
- `PolicyCheckStepVersion`.

Implementation note: issue #65 intentionally starts with a bounded
`PolicyVersion` aggregate rather than three independently activated version
tables. The aggregate snapshots Policy fields, associated PolicyRules, and
associated PolicyCheckSteps together so the review/activation unit is explicit
without introducing granular runtime version references before Runtime Gateway
versioned evaluation is designed.

Each version should include:

- stable parent ID, such as `policy_id`, `policy_rule_id`, or
  `policy_check_step_id`;
- monotonically increasing `version_number`;
- `status`;
- immutable snapshot of the versioned fields;
- `change_summary`;
- `created_by_actor_type`;
- `created_by_actor_id`;
- `updated_by_actor_type`;
- `updated_by_actor_id`;
- `review_requested_by_actor_type`;
- `review_requested_by_actor_id`;
- `reviewed_by_actor_type`;
- `reviewed_by_actor_id`;
- `review_note`;
- `created_at`;
- `updated_at`;
- `submitted_at`;
- `approved_at`;
- `rejected_at`;
- `activated_at`;
- `superseded_at`;
- `archived_at`;
- safe metadata only.

Activated versions should be immutable. If a change is needed, AGCP should
create a new draft version from the active version or from a selected previous
approved version. This prevents historical PolicyDecisions from pointing at
mutable rule content.

## Review Semantics

V1 should support a simple review loop:

1. A policy author creates a draft version or creates a draft from the current
   active version.
2. The author supplies a required change summary.
3. The author submits the draft for review.
4. A reviewer approves or rejects the version.
5. An approved version can be activated.
6. A rejected version returns to `draft` or becomes `archived`, depending on
   the implementation's simpler path.

Review should use `ActorContext` for actor attribution. Before full user auth,
this is still local and limited, but the data model should be ready for real
user identity later.

### HumanApproval Reuse

Policy review resembles HumanApproval but should not immediately reuse the
runtime HumanApproval object as-is.

Reasons:

- runtime HumanApproval is tied to one policy decision or action;
- policy review concerns authoring changes and activation;
- policy review may need diff summaries, version snapshots, and rollback
  references;
- policy review should not be confused with approval of a single runtime
  exception.

V1 can either create a separate lightweight `PolicyReview` concept later or
link policy version review actions to HumanApproval only after the semantics
are designed. Until then, audit events plus version review fields are enough.

## Activation Semantics

Only approved versions should become active.

Activating a new version should:

- mark the new version `active`;
- set `activated_at`;
- supersede any previous active version for the same logical Policy or
  PolicyRule;
- set `superseded_at` on the old active version;
- append audit records for activation and supersession.

Runtime Gateway should evaluate only active versions once versioned evaluation
is implemented.

Rollback should be explicit:

- either reactivate a previous approved version;
- or create a new draft copied from a previous approved version, review it, and
  activate it.

The safer default is copy-to-draft because it preserves review state and avoids
surprising reactivation without a fresh audit trail.

## Audit And Evidence

Suggested audit events:

- `policy_version_created`;
- `policy_version_updated`;
- `policy_version_submitted_for_review`;
- `policy_version_approved`;
- `policy_version_rejected`;
- `policy_version_activated`;
- `policy_version_superseded`;
- `policy_version_archived`;
- `policy_rule_version_created`;
- `policy_rule_version_updated`;
- `policy_rule_version_submitted_for_review`;
- `policy_rule_version_approved`;
- `policy_rule_version_rejected`;
- `policy_rule_version_activated`;
- `policy_rule_version_superseded`;
- `policy_rule_version_archived`;
- `policy_check_step_version_created`;
- `policy_check_step_version_updated`;
- `policy_check_step_version_submitted_for_review`;
- `policy_check_step_version_approved`;
- `policy_check_step_version_rejected`;
- `policy_check_step_version_activated`;
- `policy_check_step_version_superseded`;
- `policy_check_step_version_archived`.

Audit metadata should include safe IDs, version numbers, status transitions,
actor references, and short change summaries. It should not include raw
runtime payloads, source content, prompts, credentials, scanner payloads,
secrets, or full unredacted policy condition blobs if those conditions may
contain operationally sensitive details.

Evidence Bundle should later show:

- PolicyVersion ID and version number used by each PolicyDecision;
- PolicyRuleVersion ID and version number used by each PolicyDecision;
- PolicyCheckStepVersion references for CheckResults produced by authored
  checks;
- activation and review audit events relevant to those versions;
- safe change summaries when useful.

Evidence Bundle should not become a full policy diff viewer.

## Runtime Implications

No Runtime Gateway behavior changes in this issue.

Future behavior:

- Runtime Gateway evaluates only active policy/rule/check-step versions.
- PolicyDecision stores `policy_version_id` and `policy_rule_version_id` when
  available.
- CheckResults generated from authored PolicyCheckSteps can store
  `policy_check_step_version_id` in safe metadata or a typed field.
- Runtime activity and Evidence Bundle can expose version references as
  technical evidence.

Existing unversioned policy evaluation should continue until the versioning
foundation is implemented and migrated deliberately.

## UI Implications

Future Policy UI should avoid direct editing of active versions. Recommended
patterns:

- show a warning when viewing or attempting to edit active policy content;
- offer "create draft from active";
- require a change summary before review submission;
- show a compact diff summary for Policy, PolicyRule, and PolicyCheckStep
  changes;
- allow submit for review;
- allow approve or reject for authorized reviewers;
- allow activate only after approval;
- show the currently active version and previous versions;
- support rollback by copying a previous approved version into a new draft.

The UI should not present policy review as legal certification. Approval means
the organization accepted the governance configuration, not that data use is
legally certified or automatically compliant.

## V1 Recommendation

Keep V1 small:

1. Finish this design. Done when this document is merged.
2. Add immutable version tables for Policy, PolicyRule, and PolicyCheckStep.
3. Add a minimal API for draft creation, submit for review, approve, reject,
   activate, archive, and copy-from-version.
4. Update Runtime Gateway evaluation to use active versions.
5. Store policy/rule version references on PolicyDecision.
6. Add Evidence Bundle references to policy/rule/check-step versions.
7. Add frontend guardrails for draft, review, activation, and rollback.

Avoid broad workflow engines, complex RBAC frameworks, external GRC sync, and
policy simulation until the core version lifecycle is proven.

## Non-goals

- No frontend UI in this issue.
- No enterprise GRC workflow engine.
- No OIDC/SAML/JWT design or implementation in this issue.
- No team or organization-unit resolver in this issue.
- No policy simulation in this issue.
- No automatic compliance scoring.
- No legal compliance certification claims.
- No change to Runtime Gateway behavior.
- No change to policy evaluator behavior.

## Migration Path

Recommended staged implementation:

1. Design policy versioning and review guardrails.
2. Add version persistence for Policy, PolicyRule, and PolicyCheckStep.
3. Add version lifecycle API and audit events.
4. Update PolicyDecision to store active policy and rule version references.
5. Update Runtime Gateway evaluation to read active versions.
6. Include version references in Evidence Bundle and Runtime activity.
7. Add UI guardrails for draft creation, review, approval, activation, and
   rollback.
8. Add policy simulation only after active-version evaluation is stable.
9. Add richer separation-of-duties rules after real user auth and roles exist.

## Open Questions

- Should V1 version Policy as a bundle of rules, or version Policy and
  PolicyRule independently first?
- Should PolicyCheckStep versions activate with their linked PolicyRule
  version, or have an independent activation lifecycle?
- Should activation require a different actor than approval before real RBAC
  exists?
- Should rejected versions return to `draft` or become immutable rejected
  records that must be copied into a new draft?
- How much of a PolicyRule condition should be included in audit metadata
  versus only Evidence Bundle or API reads?
- Should rollback reactivate previous approved versions directly, or always
  create a new draft copied from a previous version?
- How should version references be backfilled for historical PolicyDecision
  records created before versioning?
- What minimum review workflow is useful before OIDC/SAML/JWT and team
  membership resolution exist?
