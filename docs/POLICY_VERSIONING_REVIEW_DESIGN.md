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
- Policy Studio reload hydration from the latest draft PolicyVersion snapshot,
  with active PolicyVersion and live PolicyRule fallback used only when no draft
  snapshot exists;
- a dedicated `PolicyVersionReviewRequest` workflow for draft-version review
  requests, approval, and rejection;
- explicit activation of approved PolicyVersion review requests, with
  `replace_active` required before superseding an existing active version;
- deterministic metadata-only PolicyVersion review diffs with activation and
  supersession evidence references;
- rollback draft creation from a prior approved, active, superseded, or
  archived PolicyVersion, with `source_version_id` and
  `policy_version_rollback_draft_created` audit evidence;
- Policy Reviews UI action to create a rollback draft from review diff or
  activation evidence context, with explicit copy that runtime is unchanged
  until review approval and activation;
- minimal reviewer assignment for pending `PolicyVersionReviewRequest`
  records, including assignment metadata, assignment audit evidence, and a
  decision guard that lets only the assigned reviewer or `platform_admin`
  approve or reject assigned reviews;
- safe Policy lifecycle cleanup actions: archive retains governance evidence
  and draft-only delete is blocked once versions, reviews, runtime decisions, or
  meaningful audit history exist;
- an IDE-style frontend Policy Studio with Blocks and Code DSL authoring,
  local validation, deterministic `PolicyRule.condition` JSON compilation, no
  Publish button, and backend-backed Submit for review.

Still unresolved:

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
- `PolicyVersionReviewRequest` is the policy-authoring review request object.
  It is separate from runtime `HumanApproval`.

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
- update an existing draft PolicyVersion from a Policy Studio/editor snapshot
  only while no pending review request exists for that version;
- create a pending review request for a draft PolicyVersion;
- read narrow review state for one PolicyVersion through
  `GET /policy-versions/{policy_version_id}/review-state`;
- list PolicyVersion review requests;
- assign a pending PolicyVersion review request to a reviewer actor without
  approving, rejecting, or activating the version;
- approve or reject a pending PolicyVersion review request without activation;
- activate an approved PolicyVersion review request explicitly;
- read a safe diff for a PolicyVersion review request;
- create a rollback draft from an approved, active, superseded, or archived
  PolicyVersion without changing runtime behavior;
- submit for review;
- approve;
- reject;
- activate;
- archive;
- rollback-copy compatibility.

Current audit events include:

- `policy_version_created`;
- `policy_version_draft_updated`;
- `policy_version_review_requested`;
- `policy_version_review_assigned`;
- `policy_version_review_approved`;
- `policy_version_review_rejected`;
- `policy_version_submitted_for_review`;
- `policy_version_approved`;
- `policy_version_rejected`;
- `policy_version_activated`;
- `policy_version_superseded`;
- `policy_version_archived`;
- `policy_version_rollback_draft_created`;
- `policy_version_rollback_copy_created`.
- `policy_live_edit_blocked`.

Review-linked activation now fails fast when another active version already
exists for the same Policy unless the caller explicitly sends
`replace_active=true`. With replacement, the previous active version is marked
`superseded` and the new approved review version becomes `active` in the same
transaction. A database-level partial unique index also enforces one active
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
- Submit for review creates a pending `PolicyVersionReviewRequest`;
- the Reviews page includes a Policy Reviews queue for pending and approved
  review requests;
- the Reviews page shows Policy Review Diff summaries with baseline type,
  changed condition fields, runtime effect copy, and activation/supersession
  audit references when available;
- approved review requests can be explicitly activated from that queue;
- pending review requests can be assigned to a reviewer actor from that queue;
- assignment is governance metadata only and does not approve, reject, notify,
  or activate a version;
- assigned review requests can be approved or rejected only by the assigned
  reviewer or `platform_admin`;
- the Policy Reviews UI fetches `GET /me` for current actor and role display,
  then disables unavailable approve/reject/assign/activate actions with honest
  reasons while keeping backend RBAC authoritative;
- there is no direct Publish action.

The frontend does not yet solve the full backend/domain review workflow:

- there is no reviewer directory, notification/email flow, unassign action, or
  full enterprise auth/user management;
- activation replacement is an explicit checkbox/action, not a full diff-based
  release workflow;
- the inspector review status is informational and should not be treated as a
  complete activation workflow.

This means the frontend has lowered authoring risk, but it has not eliminated
the core active-edit risk.

## What #56 Already Has

#56 already has a meaningful backend foundation:

- `PolicyVersion` persistence;
- version lifecycle statuses;
- safe aggregate snapshots;
- audit events;
- rollback-copy compatibility and rollback-draft governance semantics;
- approval separated from activation;
- dedicated PolicyVersion review requests instead of runtime HumanApproval
  reuse;
- deterministic metadata-only review diffs for PolicyVersion review requests;
- rollback draft UX from review diff/activation evidence, requiring review and
  explicit activation before runtime changes;
- minimal reviewer assignment for pending PolicyVersion review requests;
- active-version Runtime Gateway evaluation with fallback;
- optional `policy_version_id` references on PolicyDecision and Evidence
  Bundle summaries.

#56 also benefits from frontend guardrails:

- controlled authoring instead of arbitrary JSON as the main workflow;
- local validation before save;
- backend-backed Submit for review for saved draft PolicyVersions;
- no Publish action;
- no fake production simulation or compliance score.

## What #56 Still Lacks

The remaining work is narrower than the original broad design issue:

- define whether DSL source is stored in snapshots, stored only as safe UI
  metadata, or regenerated from compiled JSON;
- document that compiled deterministic condition JSON is the runtime source of
  truth for V1;
- confirm PolicyCheckSteps remain snapshotted inside the aggregate
  PolicyVersion for V1;
- decide historical PolicyDecision backfill behavior;
- decide whether an unassign endpoint is needed;
- add richer role-aware product UX later.

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
- legacy live Policy and PolicyRule mutation APIs remain for bootstrapping and
  fallback Policies without an active PolicyVersion, but direct live edits are
  blocked once a Policy has an active PolicyVersion;
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
- A draft PolicyVersion with a pending review request is immutable in V1. The
  backend rejects `PATCH /policy-versions/{policy_version_id}/draft` with 409
  and instructs callers to create a new draft for additional changes.
- Submit for review creates a pending `PolicyVersionReviewRequest`; it does not
  publish or activate anything.
- Review approval records reviewer intent on the review request; it does not
  automatically activate the PolicyVersion.
- Activation is explicit and audited through an approved review request.
- Activating a version fails if another active version already exists for the
  same Policy unless `replace_active=true` is provided.
- Replacement supersedes the previous active version in the same transaction
  and writes a `policy_version_superseded` audit event.
- Rollback should be non-destructive: create a new draft copy from an approved,
  active, or superseded version.
- Runtime and evidence should record `policy_version_id` where available.
- The UI should not expose a direct Publish button; runtime-changing
  transitions should keep using explicit Activate approved version wording.
- Policies with an active PolicyVersion should be changed through draft
  PolicyVersion snapshots, review, approval, and explicit activation rather
  than legacy live Policy/PolicyRule mutation endpoints.
- Archiving a Policy should be non-destructive and keep evidence/history.
  Archiving is blocked while an active PolicyVersion exists because runtime
  semantics should remain explicit. Delete is only a draft-only/bootstrap
  cleanup path for Policies with no PolicyVersion, review request, runtime
  decision, linked HumanApproval history, or meaningful audit history.

## Review Request Choice

Runtime `HumanApproval` is not reused directly for PolicyVersion review in V1.
AGCP now uses a dedicated `PolicyVersionReviewRequest` object for policy
authoring review.

Reasons:

- HumanApproval is tied to one runtime action or PolicyDecision;
- policy review is about authoring and activation of governance configuration;
- policy review needs version snapshots, diffs, review notes, activation
  references, and rollback history;
- reusing HumanApproval would blur runtime exception approval with policy
  lifecycle approval.

Implemented V1 path:

- create pending review requests only for draft PolicyVersions;
- reject duplicate pending review requests for the same PolicyVersion;
- expose narrow PolicyVersion review state to Policy Studio without requiring
  access to the global reviewer/admin queue;
- approve or reject requests without activating the PolicyVersion;
- keep runtime `HumanApproval` scoped to runtime tool-call decisions;
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

## Review Diff And Activation Evidence

PolicyVersion review requests now expose a deterministic metadata-only diff:

```text
GET /policy-version-review-requests/{review_request_id}/diff
```

The response compares the reviewed PolicyVersion against:

- the current active PolicyVersion for the same Policy when one exists;
- the previously active PolicyVersion if the reviewed version has already
  replaced it and activation audit metadata identifies that prior version;
- otherwise the live unversioned Policy/PolicyRule fallback when live rules
  exist;
- otherwise an explicit `baseline_type = none` state with "No active baseline
  found."

The diff includes safe Policy snapshot field changes, deterministic PolicyRule
condition field changes, PolicyCheckStep snapshot counts, review status,
whether activation is currently possible, whether replacement is required, and
plain-language runtime effect copy. It does not simulate production impact,
calculate affected agents, expose full runtime payloads, or claim compliance
status.

Activation evidence is audit-based. The diff response can include the review
request actor/timestamps, reviewer actor/timestamps, activation audit event,
supersession audit event, activated PolicyVersion id, and previous active
PolicyVersion id when replacement happened. This supports reviewer
explanation without adding automatic activation, Publish wording, or rollback
behavior.

## Non-goals

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
3. Treat PolicyVersion-backed Save draft, Submit for review, and explicit
   reviewed activation as implemented.
4. Complete remaining #68 follow-ups before adding richer activation product
   semantics: historical backfill must be decided and activation UI semantics
   must remain separate from review approval.
5. Treat rollback draft creation and minimal reviewer assignment as
   implemented.
6. Add optional unassign behavior, richer role-aware actions, and separation
   of duties later, after identity and RBAC are stronger.

## Risks

- If compatibility Policy/PolicyRule APIs are reopened for active-versioned
  Policies without review guardrails, users may bypass the Studio draft path
  and make future fallback/runtime behavior harder to explain.
- If activation UX grows before #68 backfill is settled, AGCP may overstate
  historical version coverage.
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
  draft, backend-backed Submit for review, local validation, and no Publish
  button;
- dedicated PolicyVersion review request queue with approve/reject actions.
- explicit Activate approved version action for approved review requests, with
  optional `replace_active` superseding of the previous active version.
- metadata-only Policy Review Diff UI with baseline type, changed fields, and
  activation/supersession evidence references.
- rollback draft action from prior version evidence. It creates a draft
  PolicyVersion copy only; users must submit it for review and explicitly
  activate an approved review request before runtime changes.
- minimal reviewer assignment for pending review requests. Assignment is
  governance metadata and does not approve, reject, notify, or activate.
- minimal `/me`-backed frontend current-actor display for Policy Reviews.
  Role-aware button disabling is advisory; backend authorization remains the
  source of truth.
- legacy live Policy and PolicyRule mutation guardrails. `POST /policies`
  remains available for bootstrap containers, and unversioned fallback policies
  remain editable. Once a Policy has an active PolicyVersion, direct
  `PATCH /policies/{policy_id}`, `POST /policy-rules`, and
  `PATCH /policy-rules/{rule_id}` mutations are blocked with
  `policy_live_edit_blocked` audit evidence and guidance to create a draft
  PolicyVersion instead.
- safe Policy archive/delete guardrails. `POST /policies/{policy_id}/archive`
  writes `policy_archived` and keeps PolicyVersions, PolicyRules,
  PolicyDecisions, review requests, and AuditLogs. `DELETE /policies/{policy_id}`
  is only for draft-only Policies with no governance history; governed Policies
  return a safe conflict instructing callers to archive instead.

Still unresolved:

- DSL source storage/versioning is undecided;
- historical backfill remains a #68 implementation follow-up;
- no reviewer directory, notification/email flow, unassign action, or full
  enterprise auth/user management exists.

Recommended next implementation issue: define historical PolicyDecision
backfill expectations or decide optional unassign/role-aware frontend
behavior. Do not add Publish wording, direct runtime rollback, or legal
certification claims.
