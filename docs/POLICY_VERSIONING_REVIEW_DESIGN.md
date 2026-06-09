# Policy Versioning And Review Guardrails Design

## Status

Issue #56 is partially superseded by implementation, but it is not complete as
a product workflow.

Already implemented:

- a backend `PolicyVersion` aggregate with version numbers and lifecycle state;
- snapshots of Policy fields, associated PolicyRules, and associated
  PolicyCheckSteps;
- lifecycle APIs for create, submit for review, approve, reject, activate,
  archive, and rollback-copy;
- append-only audit events for PolicyVersion lifecycle changes;
- `PolicyDecision.policy_version_id`;
- safe PolicyVersion summaries in Evidence Bundle output;
- Runtime Gateway active PolicyVersion snapshot evaluation with unversioned
  fallback;
- Policy Studio Save draft creation/update of draft PolicyVersion snapshots;
- an IDE-style frontend Policy Studio with Blocks and Code DSL authoring,
  local validation, deterministic `PolicyRule.condition` JSON compilation, no
  Publish button, and disabled Submit for review.

Still unresolved:

- formal review request semantics for policy authoring;
- frontend Submit for review wiring;
- historical PolicyDecision backfill guidance;
- whether and how Policy Studio DSL source should be stored with version
  snapshots.

Active PolicyVersion rollout details for #68 are tracked in
`docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`.

AGCP remains a governance and evidence control plane. It is not an
orchestrator, workflow engine, enterprise GRC suite, policy simulation engine,
or legal compliance certification system.

## Critical Assessment

Policy and PolicyRule editing became riskier once rules could match contextual
runtime fields, resolved inventory facts, and safe `check_*` CheckResult
outcome summaries. PolicyCheckSteps can also declare metadata checks that
Runtime Gateway may execute behind an explicit feature flag. These capabilities
help AGCP explain and govern runtime decisions, but they also mean an edit to a
condition or check declaration can change future production decisions.

Direct active edits are risky because a small condition change can broaden an
allow rule, suppress a human-review escalation, make a deny rule miss, or
change which evidence is collected for review. Without immutable versions and
review history, reviewers cannot reliably answer which configuration produced
a decision, who reviewed it, when it became active, or how to return to a known
configuration.

AGCP should still avoid overbuilding enterprise GRC workflows in V1. Full
separation of duties, complex approval chains, release calendars, legal
attestation, and external GRC synchronization depend on identity, team, and
operational models that AGCP does not yet have. The right V1 is a narrow
foundation: draft, review, approval, explicit activation, immutable active
snapshots, rollback-copy, audit, and evidence references.

The Runtime Gateway source of truth must be handled carefully. Active-version
evaluation improves auditability only if fallback behavior and deterministic
rule precedence are preserved. It should not introduce a generic policy engine,
policy simulation engine, hidden AccessGrant enforcement, or a new DSL runtime.

## Current Backend State

The backend currently uses a bounded aggregate model:

- `Policy` remains the logical policy container.
- `PolicyRule` remains the editable unversioned rule record and existing API
  contract.
- `PolicyCheckStep` remains the authored metadata-check declaration.
- `PolicyVersion` is the versioned review and activation unit.

`PolicyVersion` snapshots:

- safe Policy fields;
- associated PolicyRules, including deterministic condition JSON;
- associated PolicyCheckSteps, including deterministic metadata-check
  configuration.

`PolicyVersionStatus` currently includes:

- `draft`;
- `under_review`;
- `approved`;
- `rejected`;
- `active`;
- `superseded`;
- `archived`.

Lifecycle APIs currently exist for:

- create version from a Policy;
- create a draft PolicyVersion from a Policy Studio/editor snapshot;
- list Policy versions;
- get one PolicyVersion;
- update an existing draft PolicyVersion from a Policy Studio/editor snapshot;
- submit for review;
- approve;
- reject;
- activate;
- archive;
- rollback-copy.

Current audit events include:

- `policy_version_created`;
- `policy_version_submitted_for_review`;
- `policy_version_approved`;
- `policy_version_rejected`;
- `policy_version_activated`;
- `policy_version_archived`;
- `policy_version_rollback_copy_created`.

Activation now fails fast when another active version already exists for the
same Policy. A database-level partial unique index also enforces one active
PolicyVersion per Policy.

Runtime Gateway now prefers active PolicyVersion snapshots where available and
falls back to current unversioned Policy/PolicyRule rows when no active version
exists for a Policy. The active snapshot adapter preserves the existing
deterministic evaluator shape and rule precedence:

- deny;
- require_human_review;
- allow;
- not_applicable.

Telemetry policy evaluation uses the same active-version loader as Runtime
Gateway. Historical PolicyDecisions remain nullable/unversioned unless an
explicit conservative backfill is designed later.

## Current Frontend State

The Policy Studio frontend already solves part of the #56 product guardrail
surface:

- it replaces raw CRUD forms with an IDE-like authoring surface;
- it supports Blocks and Code DSL modes;
- it organizes authoring around `WHEN -> CHECK -> THEN -> PROVE`;
- it compiles to deterministic `PolicyRule.condition` JSON;
- unsupported DSL lines block saving;
- local validation is clearly not runtime simulation;
- static templates are authoring helpers, not backend records;
- Save draft writes a draft `PolicyVersion` snapshot through the backend draft
  version APIs;
- existing Policy/PolicyRule APIs remain available for compatibility, but the
  user-facing Studio draft is now the version snapshot;
- Submit for review is disabled;
- there is no direct Publish action.

The frontend does not yet solve the backend/domain review workflow:

- Submit for review is not wired to backend lifecycle APIs;
- there is no policy review queue, reviewer assignment, diff view, or
  role-aware review UI;
- the inspector review status is informational and should not be treated as a
  complete review workflow.

This means the frontend has lowered authoring risk, but it has not eliminated
the core active-edit risk.

## What #56 Already Has

#56 already has a meaningful backend foundation:

- `PolicyVersion` persistence;
- version lifecycle statuses;
- safe aggregate snapshots;
- audit events;
- rollback-copy semantics;
- approval separated from activation;
- active-version Runtime Gateway evaluation with fallback;
- optional `policy_version_id` references on PolicyDecision and Evidence
  Bundle summaries.

#56 also benefits from frontend guardrails:

- controlled authoring instead of arbitrary JSON as the main workflow;
- local validation before save;
- disabled Submit for review;
- no Publish action;
- no fake production simulation or compliance score.

## What #56 Still Lacks

The remaining work is narrower than the original broad design issue:

- define formal review request semantics;
- decide whether review should use only PolicyVersion review fields and audit
  events or add a dedicated `PolicyReviewRequest`;
- avoid reusing runtime `HumanApproval` as-is for policy authoring review;
- define whether DSL source is stored in snapshots, stored only as safe UI
  metadata, or regenerated from compiled JSON;
- document that compiled deterministic condition JSON is the runtime source of
  truth for V1;
- confirm PolicyCheckSteps remain snapshotted inside the aggregate
  PolicyVersion for V1;
- decide historical PolicyDecision backfill behavior;
- define rollback-copy UX and API expectations;
- wire frontend Submit for review only after the review contract is agreed.

## Proposed V1 Model

The current aggregate `PolicyVersion` model is the right minimal V1 foundation.
It should remain the review and activation unit until there is strong evidence
that independently activated PolicyRuleVersion or PolicyCheckStepVersion tables
are needed.

V1 source-of-truth rules:

- active runtime evaluation uses immutable active PolicyVersion snapshots where
  available;
- unversioned Policy/PolicyRule rows remain fallback and editing compatibility
  records until migration is complete;
- compiled deterministic `PolicyRule.condition` JSON is the runtime source of
  truth;
- Policy Studio DSL source is an authoring representation, not a runtime
  language;
- if DSL source is stored later, it should be safe display metadata and should
  never replace compiled condition JSON;
- PolicyCheckSteps are versioned through `check_step_snapshots` in the
  aggregate PolicyVersion.

Recommended product semantics:

- Save draft creates or updates draft PolicyVersion content and does not
  activate, submit for review, or mutate active runtime configuration.
- Submit for review should create a review state or review request; it should
  not publish or activate anything.
- Approval should make a version eligible for activation; it should not
  automatically activate the version.
- Activation should be explicit and audited.
- Activating a version fails if another active version already exists for the
  same Policy.
- Rollback should be non-destructive: create a new draft copy from an approved,
  active, or superseded version.
- Runtime and evidence should record `policy_version_id` where available.
- The UI should not expose a direct Publish button before review and
  activation semantics are fully designed.

## Review Request Choice

Runtime `HumanApproval` should not be reused directly for PolicyVersion review
in V1.

Reasons:

- HumanApproval is tied to one runtime action or PolicyDecision;
- policy review is about authoring and activation of governance configuration;
- policy review needs version snapshots, diffs, review notes, activation
  references, and rollback history;
- reusing HumanApproval would blur runtime exception approval with policy
  lifecycle approval.

Recommended V1 path:

- keep the existing PolicyVersion review fields and audit events for the
  minimal lifecycle;
- add a dedicated lightweight `PolicyReviewRequest` only if a review inbox,
  reviewer assignment, or multi-step review queue becomes necessary;
- do not claim policy approval is legal certification.

## Evidence And Telemetry

Evidence should continue to include safe PolicyVersion summaries instead of
full raw snapshots. Safe summaries can include:

- `policy_version_id`;
- `policy_id`;
- `version_number`;
- `status`;
- `activated_at`;
- safe `change_summary`.

Evidence should not expose raw prompts, source contents, credentials, runtime
payloads, or unsafe snapshot metadata. It should not become a full policy diff
viewer.

Telemetry rollout details are tracked in
`docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`. Runtime Gateway and telemetry can now
reference active PolicyVersion snapshots for new decisions, but historical
PolicyDecision records remain nullable unless a future explicit backfill task
is designed.

## Non-goals

- No backend review endpoints in this design cleanup task.
- No migrations in this design cleanup task.
- No frontend Publish button.
- No fake review status.
- No policy simulation engine.
- No generic runtime DSL.
- No change to deterministic evaluator precedence.
- No enterprise GRC workflow.
- No OIDC/SAML/JWT.
- No legal compliance certification claims.
- No compliance scores.

## Implementation Sequence

Recommended next sequence:

1. Treat #58 as implemented if the current Policy Studio V1 satisfies the
   product acceptance bar; split remaining direct no-code block editing and
   PolicyCheckStep authoring into narrower follow-ups.
2. Keep #76 open or partial until `docs/POLICY_STUDIO_DSL_DESIGN.md` defines
   grammar, operators, supported fields, storage/versioning, diffs, and
   unsupported-line behavior.
3. Use this refreshed #56 design to narrow review workflow work around Submit
   for review, approval, activation, and rollback-copy.
4. Complete #68 follow-ups before exposing activation or Publish semantics:
   historical backfill must be decided and activation UI semantics must remain
   separate from review approval.
5. Implement a backend Policy Review Workflow only after #56 and #68 decisions
   are settled.
6. Wire Policy Studio Submit for review to the backend review lifecycle.
7. Add review inbox, diff UI, role-aware review actions, and separation of
   duties later, after identity and RBAC are stronger.

## Risks

- If existing compatibility Policy/PolicyRule APIs remain directly editable,
  users may still bypass the Studio draft path unless later guardrails or
  role-aware product flows make the intended lifecycle clearer.
- If activation is exposed before #68 is settled, AGCP may have inconsistent
  runtime and telemetry sources of truth.
- If DSL source is treated as runtime source of truth too early, AGCP risks
  introducing an unsupported policy language.
- If HumanApproval is reused for policy authoring review, runtime exception
  approvals and policy lifecycle approvals may become confusing.
- If evidence exports include full snapshots, they may expose unsafe metadata
  or operational details.
- If AGCP uses Publish wording too early, users may infer production or legal
  certification semantics that do not exist.

## GitHub Issue #56 Comment-Ready Summary

Current repo state partially supersedes #56 but does not close it as a product
workflow.

Implemented:

- backend `PolicyVersion` aggregate snapshots for Policy, PolicyRule, and
  PolicyCheckStep configuration;
- lifecycle statuses and APIs for draft, review, approval, activation,
  archive, and rollback-copy;
- lifecycle audit events;
- active PolicyVersion Runtime Gateway evaluation with unversioned fallback;
- `PolicyDecision.policy_version_id` and safe Evidence Bundle summaries;
- frontend Policy Studio guardrails with Blocks/DSL, PolicyVersion-backed Save
  draft, local validation, disabled Submit for review, and no Publish button.

Still unresolved:

- Submit for review is not wired;
- formal review request object semantics are undecided;
- DSL source storage/versioning is undecided;
- historical backfill remains a #68 implementation follow-up;
- no review inbox, diff UI, reviewer assignment, or role-aware policy review
  workflow exists.

Recommended next implementation issue: define and implement the PolicyVersion
review workflow contract for Policy Studio, but only after historical backfill
and activation semantics are explicitly scoped if that work includes
activation.
