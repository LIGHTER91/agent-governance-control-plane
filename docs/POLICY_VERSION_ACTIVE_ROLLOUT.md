# Active PolicyVersion Rollout And Telemetry Migration

## Status

Issue #68 started as a rollout and migration planning issue. Runtime Gateway
and telemetry now use the same active PolicyVersion evaluation loader, and the
single-active-version invariant is enforced in application code plus a
database-level partial unique index. Historical backfill remains a follow-up
task.

Current state:

- Runtime Gateway decision evaluation already uses active PolicyVersion
  snapshots where available.
- Runtime Gateway falls back to unversioned active Policy/PolicyRule rows for
  Policies without an active PolicyVersion.
- Runtime Gateway stores `policy_version_id` on new PolicyDecision records when
  the selected rule came from an active PolicyVersion snapshot.
- Telemetry ingestion now uses the same active PolicyVersion evaluation loader
  as Runtime Gateway.
- Telemetry stores `policy_version_id` on new PolicyDecision records when the
  selected rule came from an active PolicyVersion snapshot.
- Telemetry falls back to unversioned active Policy/PolicyRule rows when no
  active PolicyVersion exists for a Policy.
- Historical PolicyDecision records are not backfilled.
- The single-active-version invariant is enforced by activation API validation
  and a partial unique index on `policy_versions(policy_id)` where
  `status = 'active'`.
- Approved PolicyVersion review requests can now be explicitly activated.
  Approval alone still has no runtime effect.
- If another active version exists, activation requires `replace_active=true`;
  replacement supersedes the previous active version in the same transaction.
- PolicyVersion review requests now expose deterministic metadata-only review
  diffs and activation/supersession audit references. These diffs explain what
  is being reviewed or activated; they do not simulate production impact.
- Safe Policy lifecycle cleanup is implemented. Archive is non-destructive and
  blocked while a Policy has an active PolicyVersion. Delete is limited to
  draft-only Policies with no governance history.

AGCP remains a governance and evidence control plane. It does not execute
tools, replace orchestrators, provide legal certification, or run a production
policy simulation engine.

## Critical Assessment

Active PolicyVersion evaluation is the right target because immutable active
snapshots improve review safety and auditability. A PolicyDecision is more
explainable when it can point to the exact reviewed Policy, PolicyRule, and
PolicyCheckStep configuration that was active at decision time.

Changing the runtime source of truth is still risky. AGCP has two ingestion
paths today: Runtime Gateway decisions and telemetry events. They now share the
same policy evaluation loader, which reduces source-of-truth drift. The rollout
is not fully complete until historical records and backfill expectations are
handled.

Fallback behavior must be preserved. Existing local demos, tests, and early
integrations still rely on unversioned Policy/PolicyRule rows. Removing
fallback or requiring every Policy to have an active PolicyVersion would break
current behavior and make local development harder.

Rule precedence must not change. The rollout should continue to use the
existing deterministic evaluator and matching semantics:

- deny;
- require_human_review;
- allow;
- not_applicable.

The rollout should not introduce a generic policy engine, a runtime DSL, hidden
AccessGrant enforcement, policy simulation, or GRC workflow automation. It
should only make reviewed snapshots the preferred runtime input and ensure the
result is recorded safely for evidence.

## Current Source Of Truth

### Runtime Gateway

`POST /runtime/tool-calls/decision` currently uses a mixed source of truth:

- active PolicyVersion snapshots are preferred per Policy;
- unversioned active Policy/PolicyRule rows are used for Policies without an
  active PolicyVersion;
- non-active PolicyVersions are ignored;
- the single-active-version guard should prevent multiple active
  PolicyVersions for one Policy, but the runtime loader remains deterministic
  if invalid pre-constraint data is present.

This path is not feature-flagged today. It is the current Runtime Gateway
behavior.

### Telemetry

`POST /telemetry/events` now uses the same mixed source of truth as Runtime
Gateway:

- active PolicyVersion snapshots are preferred per Policy;
- unversioned active Policy/PolicyRule rows are used for Policies without an
  active PolicyVersion;
- non-active PolicyVersions are ignored;
- new versioned telemetry decisions store `policy_version_id`.

The Runtime Gateway endpoint still rejects `mode = telemetry` and directs
callers to `POST /telemetry/events`; the endpoint contract did not change.

## What PolicyVersion Snapshots Contain

The current aggregate `PolicyVersion` snapshot includes safe, bounded
configuration only.

Policy snapshot:

- `id`;
- `name`;
- `description`;
- `status`.

PolicyRule snapshots:

- `id`;
- `policy_id`;
- `name`;
- `description`;
- `condition`.

The `condition` field is the compiled deterministic JSON string used by the
existing evaluator. The frontend Code DSL is not stored in the snapshot today.
For V1, compiled condition JSON should remain the runtime source of truth. DSL
source may be added later as safe authoring metadata after the controlled DSL
design is completed, but it should not replace compiled JSON.

PolicyCheckStep snapshots:

- `id`;
- `policy_rule_id`;
- `check_tool_id`;
- `check_type`;
- `target_selector`;
- `required`;
- `failure_behavior`;
- `min_confidence`;
- `status`;
- `evidence_retention`;
- safe filtered `metadata`.

Review and activation metadata is stored on the PolicyVersion row, not inside
the snapshots:

- lifecycle `status`;
- `change_summary`;
- actor fields for creator, review requester, and reviewer;
- `review_note`;
- lifecycle timestamps for submitted, approved, rejected, activated,
  superseded, and archived states.

## PolicyDecision Version References

`PolicyDecision.policy_version_id` exists as a nullable foreign key to
`policy_versions.id`.

Current behavior:

- Runtime Gateway decisions produced from active PolicyVersion snapshots store
  the selected PolicyVersion ID.
- Runtime Gateway fallback decisions store `policy_version_id = null`.
- Telemetry decisions produced from active PolicyVersion snapshots store the
  selected PolicyVersion ID.
- Telemetry fallback decisions store `policy_version_id = null`.
- Historical PolicyDecision records remain nullable and should continue to be
  readable.

This is correct for the current rollout state. Version references must be
presented in evidence and activity surfaces as optional context, not as proof
that every historical decision was versioned.

## Evidence Bundle Behavior

Evidence Bundle export already renders safe PolicyVersion summaries when a
PolicyDecision has `policy_version_id`.

Safe summary fields:

- `policy_version_id`;
- `policy_id`;
- `version_number`;
- `status`;
- `activated_at`;
- safe `change_summary`.

Evidence should not include full raw PolicyVersion snapshots, DSL source,
runtime payloads, prompts, source contents, credentials, or unsafe metadata.

CheckResult summaries can surface PolicyVersion context through linked
PolicyDecisions when available. Agent-scoped CheckResults without a linked
PolicyDecision remain unversioned.

## Single-Active-Version Invariant

Current invariant:

- application-level activation logic fails fast when another active version
  already exists for the same Policy unless the reviewed activation request
  explicitly sets `replace_active=true`;
- replacement marks the previous active version `superseded` before activating
  the newly reviewed version;
- runtime loading defensively selects one active version if multiple active
  versions exist in invalid pre-constraint data;
- the database enforces unique `(policy_id, version_number)`;
- the database also enforces one active PolicyVersion per Policy with the
  `uq_policy_versions_one_active_per_policy` partial unique index.

Migration behavior:

- the migration creates a unique partial index on `policy_id` where
  `status = 'active'`;
- deployments with duplicate active PolicyVersions for one Policy must resolve
  those duplicates before applying the migration;
- the migration does not silently pick a winner, supersede, archive, or delete
  existing records.

## Historical PolicyDecision Strategy

Historical records should remain untouched by default.

Reasons:

- older decisions may have been produced before a PolicyVersion existed;
- unversioned PolicyRule rows may have changed since the decision;
- inferring a historical version after the fact can produce misleading
  evidence;
- nullable `policy_version_id` already represents unversioned or unknown
  version context safely.

Optional future backfill should be explicit and conservative:

- only backfill when the decision timestamp falls within a known active
  PolicyVersion interval;
- only backfill when `policy_id` and `rule_id` match a snapshot;
- record a backfill audit event or migration report;
- never mutate decision, reason, or rule matching outputs;
- document that backfilled version references are inferred metadata, not
  re-evaluated decisions.

Until that exists, historical decisions should be documented as unversioned
when `policy_version_id` is null.

## Target Behavior

The target runtime/evidence behavior is now partially reached:

- Runtime Gateway and telemetry use the same policy evaluation loader.
- Active PolicyVersion snapshots are preferred where available.
- Unversioned active Policy/PolicyRule fallback remains available for Policies
  without active versions.
- New PolicyDecision records store `policy_version_id` when the matched rule
  came from an active PolicyVersion.
- New fallback decisions keep `policy_version_id = null`.
- Historical decisions remain readable with nullable version references.
- Evidence exports include safe version summaries when available and honest
  unversioned states otherwise.
- Legacy live Policy and PolicyRule mutation endpoints remain for bootstrap and
  unversioned fallback Policies, but direct live edits are blocked once a
  Policy has an active PolicyVersion. Changes to versioned Policies should go
  through draft PolicyVersion snapshots, review, approval, and explicit
  activation.
- Policy archive/delete actions do not change active-version runtime semantics.
  Archive keeps evidence/history and refuses active-versioned Policies until
  the active version is superseded or otherwise deactivated. Delete is only a
  draft-only cleanup path for Policies with no versions, reviews, runtime
  decisions, linked HumanApproval history, or meaningful audit history.

Remaining target behavior:

- Historical backfill, if needed, is explicit and conservative.
- Policy Studio Save draft writes draft PolicyVersion snapshots and does not
  affect runtime until activation.
- Policy Studio Submit for review creates a dedicated pending
  PolicyVersionReviewRequest for a saved draft snapshot and does not affect
  runtime.
- Review approval and rejection record reviewer intent only; they do not
  activate a PolicyVersion.
- Activation is explicit through an approved PolicyVersion review request and
  changes runtime policy evaluation for future Runtime Gateway and telemetry
  decisions.

## Rollout Sequence

Recommended sequence:

1. Keep unversioned fallback behavior. Implemented.
2. Treat Runtime Gateway active-version evaluation as implemented and validated
   by targeted backend tests.
3. Document current mixed behavior clearly in roadmap and evidence docs.
   Implemented.
4. Replace `load_active_policy_evaluation_rules` in telemetry ingestion with
   the same runtime policy evaluation config used by Runtime Gateway.
   Implemented.
5. Add tests proving telemetry. Implemented for:
   - uses active PolicyVersion snapshots when present;
   - ignores draft, under_review, approved, rejected, superseded, and archived
     versions;
   - preserves unversioned fallback;
   - persists `policy_version_id` for versioned decisions;
   - keeps idempotency and HumanApproval creation behavior unchanged.
6. Add a dedicated single-active-version hardening task with a PostgreSQL
   partial unique index and cleanup guidance. Implemented.
7. Decide whether historical backfill is needed. If yes, implement it as an
   explicit administrative migration/report path, not as automatic runtime
   behavior.
8. Policy Studio Save draft writes draft PolicyVersion snapshots. Implemented.
9. Add Policy Studio Submit for review and a minimal Policy Reviews queue with
   no activation side effects. Implemented.
10. Add explicit Activate approved version workflow for approved review
    requests. Implemented.
11. Add deterministic metadata-only Policy Review Diff and activation evidence
    for review requests. Implemented.
12. Add rollback draft creation from prior PolicyVersion evidence, without
    direct runtime rollback or automatic activation. Implemented.
13. Add guardrails around legacy live Policy/PolicyRule mutation endpoints so
    active-versioned Policies cannot bypass review. Implemented.
14. Add safe Policy archive/delete guardrails without runtime rollback,
    automatic activation, or destructive governance-history deletion.
    Implemented.
15. Keep Publish out of the UI.

## Implementation Follow-Ups

Recommended next implementation issues:

1. Decide and document whether historical PolicyDecision backfill is required.
2. Decide whether any admin-only legacy live edit override is needed later.
   Default product behavior should keep active-versioned Policies on the
   draft/review/activation path.

## Non-goals

- No Publish button.
- No fake activation semantics.
- No policy simulation engine.
- No legal compliance certification claims.
- No orchestration or tool execution.
- No broad enterprise GRC workflow.
- No review workflow side effects on runtime evaluation.
- No direct Publish action or wording.
