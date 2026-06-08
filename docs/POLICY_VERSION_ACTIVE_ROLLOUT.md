# Active PolicyVersion Rollout And Telemetry Migration

## Status

Issue #68 is a rollout and migration planning issue. It should remain
documentation-first until the remaining behavior changes are split into narrow
implementation tasks.

Current state:

- Runtime Gateway decision evaluation already uses active PolicyVersion
  snapshots where available.
- Runtime Gateway falls back to unversioned active Policy/PolicyRule rows for
  Policies without an active PolicyVersion.
- Runtime Gateway stores `policy_version_id` on new PolicyDecision records when
  the selected rule came from an active PolicyVersion snapshot.
- Telemetry ingestion still evaluates unversioned active Policy/PolicyRule
  rows.
- Historical PolicyDecision records are not backfilled.
- The single-active-version invariant is enforced by lifecycle application
  logic and defensive runtime selection, not by a database constraint.

AGCP remains a governance and evidence control plane. It does not execute
tools, replace orchestrators, provide legal certification, or run a production
policy simulation engine.

## Critical Assessment

Active PolicyVersion evaluation is the right target because immutable active
snapshots improve review safety and auditability. A PolicyDecision is more
explainable when it can point to the exact reviewed Policy, PolicyRule, and
PolicyCheckStep configuration that was active at decision time.

Changing the runtime source of truth is still risky. AGCP has two ingestion
paths today: Runtime Gateway decisions and telemetry events. If only Runtime
Gateway uses active PolicyVersions, operators can observe different
policy-version behavior depending on which endpoint a runtime integration uses.
That is acceptable as a transitional state only when it is clearly documented.

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
- if multiple active PolicyVersions exist for one Policy, the runtime loader
  defensively selects the latest by version number, activation timestamp, and
  ID.

This path is not feature-flagged today. It is the current Runtime Gateway
behavior.

### Telemetry

`POST /telemetry/events` currently uses the legacy unversioned source of truth:

- active Policy rows;
- associated PolicyRule rows;
- no PolicyVersion snapshots.

The Runtime Gateway endpoint rejects `mode = telemetry` and directs callers to
`POST /telemetry/events`, so telemetry migration must be planned explicitly.

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
- Telemetry decisions store `policy_version_id = null` because telemetry still
  uses the unversioned evaluator path.
- Historical PolicyDecision records remain nullable and should continue to be
  readable.

This is correct for the current mixed rollout state. It must be clearly
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

- application-level activation logic supersedes active versions for the same
  Policy before marking the approved version active;
- runtime loading defensively selects one active version if multiple active
  versions exist;
- the database only enforces unique `(policy_id, version_number)`;
- there is no database-level unique constraint for one active PolicyVersion per
  Policy.

Recommended target:

- add a PostgreSQL partial unique index on `policy_id` where `status = 'active'`;
- add migration tests for the constraint shape;
- add transition tests proving activation remains transactional;
- include cleanup guidance for any accidental multiple-active rows before the
  constraint is introduced.

This should be implemented as a dedicated backend hardening task before
activation is exposed as product workflow. It does not need to be added in this
planning pass because it is a migration and behavior-hardening change.

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

The target runtime/evidence behavior is:

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
- A database guard prevents multiple active PolicyVersions for the same Policy.
- Frontend Submit for review and any activation workflow are only enabled after
  these semantics are implemented and validated.

## Rollout Sequence

Recommended sequence:

1. Keep unversioned fallback behavior.
2. Treat Runtime Gateway active-version evaluation as implemented and validated
   by targeted backend tests.
3. Document current mixed behavior clearly in roadmap and evidence docs.
4. Add a dedicated telemetry migration task that replaces
   `load_active_policy_evaluation_rules` in telemetry ingestion with the same
   runtime policy evaluation config used by Runtime Gateway.
5. Add tests proving telemetry:
   - uses active PolicyVersion snapshots when present;
   - ignores draft, under_review, approved, rejected, superseded, and archived
     versions;
   - preserves unversioned fallback;
   - persists `policy_version_id` for versioned decisions;
   - keeps idempotency and HumanApproval creation behavior unchanged.
6. Add a dedicated single-active-version hardening task with a PostgreSQL
   partial unique index and cleanup guidance.
7. Decide whether historical backfill is needed. If yes, implement it as an
   explicit administrative migration/report path, not as automatic runtime
   behavior.
8. Only after the above, implement Policy Studio Submit for review and review
   workflow wiring.
9. Keep Publish out of the UI unless a later issue explicitly defines reviewed
   activation semantics.

## Implementation Follow-Ups

Recommended next implementation issues:

1. Migrate telemetry ingestion to `load_runtime_policy_evaluation_config` while
   preserving fallback, idempotency, and HumanApproval behavior.
2. Add a database-level single-active PolicyVersion guard and migration tests.
3. Decide and document whether historical PolicyDecision backfill is required.
4. Implement PolicyVersion-backed Save draft and Submit for review semantics
   after telemetry and single-active behavior are settled.

## Non-goals

- No frontend UI.
- No Publish button.
- No Submit for review implementation.
- No fake activation semantics.
- No policy simulation engine.
- No legal compliance certification claims.
- No orchestration or tool execution.
- No broad enterprise GRC workflow.
- No migrations in this planning pass.

