# Policy Studio Issue Alignment

This note aligns the current repository state with the open Policy Studio,
frontend rebuild, policy versioning, and runtime context issues. It is a
roadmap cleanup artifact, not a new backend feature plan.

AGCP remains a governance and evidence control plane. The Policy Studio helps
users author deterministic governance policy inputs; it does not execute tools,
does not certify legal compliance, and does not provide a production policy
simulation engine.

## Current Policy Studio State

The `/policies` route is now an IDE-style frontend surface:

- repository-style Policy and PolicyRule sidebar backed by `GET /policies` and
  `GET /policies/{policy_id}/rules`;
- static built-in templates that load unsaved local drafts only;
- block and Code DSL authoring modes using `WHEN -> CHECK -> THEN -> PROVE`;
- deterministic frontend compiler from the supported DSL subset to
  `PolicyRule.condition` JSON;
- local validation console for parser errors, unsupported DSL, generated JSON,
  selected Policy/PolicyRule state, and save readiness;
- inspector with summary, decision flow, compiled output, review status, and
  Submit for review for saved draft PolicyVersion snapshots;
- Save draft through draft PolicyVersion snapshots;
- no Publish action, no fake compliance score, and no fake production
  simulation.

## Issue-by-Issue Assessment

### #58 Policy Studio guided contextual authoring

Status: implementation mostly complete, with follow-up UX depth remaining.

Implemented:

- Raw JSON is no longer the primary authoring workflow.
- Users can start from templates, inspect blocks, use a controlled DSL, and
  save editor output as draft PolicyVersion snapshots.
- Plain-language summary and compiled deterministic JSON preview are available.
- Unsupported DSL lines are surfaced and block saving instead of being silently
  persisted.
- Backend validation errors and backend-unavailable states remain visible.
- The complex confidential-data vectorization case exists as a static template
  using supported condition fields where current backend semantics allow it.

Partially implemented:

- The block view is a readable/selectable projection of the DSL condition, but
  it is not yet a fully no-code form builder for every field.
- PolicyCheckStep concepts are reflected through CHECK/check outcome fields,
  but dedicated PolicyCheckStep authoring UI is still missing.
- Declared runtime context versus resolved inventory/check context is visible
  through field grouping and summaries, but could use stronger inline
  explanations.

Still missing:

- Fully guided question-based authoring for non-technical users.
- Rich field-level help and progressive disclosure for every contextual field.
- Policy review/version lifecycle actions in the frontend.

Recommended GitHub action: close #58 as implemented if the current IDE-style
surface is accepted as V1, or keep a narrower follow-up for direct no-code block
editing and PolicyCheckStep authoring.

### #76 Controlled Policy Studio DSL

Status: partially implemented as frontend prototype; design deliverable still
missing.

Implemented:

- A bounded frontend DSL exists with `policy`, `when`, `and`, `check`, `then`,
  and `prove` structure.
- The DSL maps only to supported deterministic PolicyRule condition fields.
- Unsupported DSL lines are reported and prevent Save draft.
- The DSL supports the four current decisions: `allow`, `deny`,
  `require_human_review`, and `not_applicable`.
- Static templates compile to the supported DSL subset.
- Smoke checks exercise round-trip cases, invalid reason, invalid
  `check_min_confidence`, unsupported syntax, empty policy, and templates.

Partially implemented:

- Blocks and DSL share one frontend compiler, but Blocks are not yet a complete
  bidirectional field editor.
- PROVE is evidence intent and documentation in the UI, not a persisted backend
  clause.
- CHECK currently compiles to deterministic `check_*` and inventory/context
  fields; it does not create or edit PolicyCheckStep records.

Still missing:

- `docs/POLICY_STUDIO_DSL_DESIGN.md` or equivalent formal design document.
- Explicit grammar, operator, storage, diff, version snapshot, and deprecation
  decisions.
- Decision on whether DSL source should be persisted as display metadata in
  PolicyVersion snapshots.

Recommended GitHub action: keep #76 open or mark partially implemented until a
formal DSL design document exists.

### #56 Policy versioning and review guardrails

Status: partially superseded by implementation, but not complete as a product
review workflow.

Why it matters now:

- The Policy Studio can make PolicyRule edits easier and more powerful.
- Direct edits to active Policies or PolicyRules can affect future runtime
  decisions.
- Backend `PolicyVersion` persistence, lifecycle APIs, audit events,
  Runtime Gateway active-version evaluation, and Evidence Bundle references
  already exist.
- Save draft now writes draft PolicyVersion snapshots and does not affect
  runtime until explicit activation.
- Submit for review now creates a dedicated pending
  PolicyVersionReviewRequest for a saved draft snapshot.
- Approving or rejecting a review request records reviewer intent only and does
  not activate the PolicyVersion.
- Approved review requests can now be activated explicitly. Replacement of an
  existing active version requires explicit `replace_active` intent.
- Review/version guardrails must still define rollback-copy UX, review diffs,
  reviewer assignment, and historical backfill.

Recommended next step: use
`docs/POLICY_VERSIONING_REVIEW_DESIGN.md` as the narrowed #56 review workflow
contract before adding rollback, diff, assignment, or publish-like semantics.

### #68 Active PolicyVersion rollout and telemetry migration

Status: should remain open for historical-backfill planning before richer
activation or publish-like workflow semantics.

Why it matters:

- Runtime Gateway can evaluate active PolicyVersion snapshots with unversioned
  fallback, as documented in `docs/POLICY_VERSION_ACTIVE_ROLLOUT.md`, but
  rollout/backfill and telemetry migration questions remain.
- Telemetry policy evaluation now uses the same active-version loader as
  Runtime Gateway, while historical PolicyDecision backfill still needs an
  explicit migration decision.
- A single-active-version guard now exists in API validation and as a
  database-level partial unique index.

Recommended next step: decide historical backfill, then refine activation UI
semantics with diffs and assignment. Do not add Publish.

### #57 Product UI rebuild

Status: largely implemented as V1 frontend product shell and connected
workflow surfaces.

Implemented:

- Shared AGCP Studio shell and navigation.
- Connected Agents, Agent detail, Human Approvals, Evidence, Runtime activity,
  Access & Data, Integration Hub, and Policy Studio surfaces.
- Product copy preserves governance/evidence control-plane boundaries.

Remaining:

- Frontend auth and role-aware UI.
- Deeper review workflows, inventory management surfaces, and richer activity
  filtering.

Recommended GitHub action: close #57 if V1 shell/rebuild is accepted, or keep
follow-ups scoped to role-aware product workflows rather than broad rebuild.

### #74 Frontend product blueprint

Status: partially satisfied by the implemented product shell and current docs,
but the requested `docs/FRONTEND_PRODUCT_BLUEPRINT.md` deliverable is not
present.

Recommended action: keep #74 open or mark partial until a concise blueprint
document exists, or explicitly decide that the implemented AGCP Studio shell
and current docs supersede the original blueprint deliverable.

### #61 Policy pre-check integrations

Status: design/foundation area remains separate from Policy Studio V1.

Current relationship to Policy Studio:

- Policy Studio CHECK blocks currently compile to existing deterministic
  condition fields and safe `check_*` summaries.
- External scanner/control-tool adapters remain out of scope.
- PolicyCheckStep authoring UI should wait until versioning/review and
  simulation semantics have a safe path.

### #50 Resolve inventory context for runtime decisions

Status: implemented in backend and reflected by current Policy Studio fields.

Current relationship to Policy Studio:

- The DSL and templates expose supported resolved-context fields such as
  AccessGrant status, Data Usage Profile review status, Source/Model/Capability
  status, classification, model provider type, and check outcome fields.
- Access Grants and Data Usage Profiles remain context/evidence inputs unless
  explicit PolicyRules use those fields.

## Recommended Implementation Sequence

1. Close or mark #58 implemented if the current Policy Studio V1 satisfies the
   product acceptance bar; create narrower follow-ups for direct no-code block
   editing and PolicyCheckStep authoring.
2. Keep #76 open or mark partial until a formal
   `docs/POLICY_STUDIO_DSL_DESIGN.md` exists.
3. Treat review request semantics, frontend Submit for review wiring, and
   explicit Activate approved version as implemented for V1.
4. Complete the remaining #68 historical-backfill decision before adding
   publish-like semantics or claiming complete historical version coverage.
5. Add review diffs, assignment, and rollback-copy UX as focused follow-ups.

## Guardrails

- Do not add a direct Publish action; use explicit Activate approved version
  wording for runtime-changing transitions.
- Do not call local validation production simulation.
- Do not invent policy impact metrics, affected-system counts, compliance
  scores, or legal certification claims.
- Keep templates as static authoring helpers unless a backend template model is
  explicitly designed later.
- Keep runtime execution responsibility with caller/orchestrator integrations;
  AGCP governs decisions and evidence.
