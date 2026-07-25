# GitHub Backlog Cleanup — Prepared Commands

Status: prepared, not applied.

The GitHub CLI was not installed in the stabilization environment, so issues
#56 and #57 were not inspected, commented on, closed, or replaced remotely.
The commands below target:

```text
LIGHTER91/agent-governance-control-plane
```

Before applying, install/authenticate `gh` and confirm the issue scopes:

```powershell
$repo = "LIGHTER91/agent-governance-control-plane"
gh auth status
gh issue view 56 --repo $repo
gh issue view 57 --repo $repo
```

## Issue #56 completion comment

Exact proposed comment:

> The requested V1 PolicyVersion review lifecycle is implemented and covered
> by the current backend/frontend test suites:
>
> - Policy Studio saves immutable draft PolicyVersion snapshots.
> - Submit for review creates a dedicated PolicyVersionReviewRequest.
> - Pending review requests support explicit reviewer assignment.
> - Assigned reviewers or platform admins can approve or reject; neither action
>   activates runtime behavior.
> - Reviewers can inspect a deterministic metadata-only diff against the active
>   or unversioned baseline, including activation/supersession evidence where
>   available.
> - Activation is a separate explicit action for an approved review request.
> - Replacing an active version requires explicit intent, and API plus database
>   guards enforce one active PolicyVersion per Policy.
> - Prior versions can create rollback drafts; rollback remains review- and
>   activation-gated.
> - Policies with active versions block legacy live Policy/PolicyRule edits and
>   emit audit evidence directing authors to the draft/review path.
>
> Approval is not Publish, AGCP does not execute tools, and historical
> PolicyDecision backfill remains a separate evidence-history decision rather
> than unfinished scope for this V1 lifecycle.

Commands:

```powershell
$repo = "LIGHTER91/agent-governance-control-plane"
$issue56Comment = @'
The requested V1 PolicyVersion review lifecycle is implemented and covered by the current backend/frontend test suites:

- Policy Studio saves immutable draft PolicyVersion snapshots.
- Submit for review creates a dedicated PolicyVersionReviewRequest.
- Pending review requests support explicit reviewer assignment.
- Assigned reviewers or platform admins can approve or reject; neither action activates runtime behavior.
- Reviewers can inspect a deterministic metadata-only diff against the active or unversioned baseline, including activation/supersession evidence where available.
- Activation is a separate explicit action for an approved review request.
- Replacing an active version requires explicit intent, and API plus database guards enforce one active PolicyVersion per Policy.
- Prior versions can create rollback drafts; rollback remains review- and activation-gated.
- Policies with active versions block legacy live Policy/PolicyRule edits and emit audit evidence directing authors to the draft/review path.

Approval is not Publish, AGCP does not execute tools, and historical PolicyDecision backfill remains a separate evidence-history decision rather than unfinished scope for this V1 lifecycle.
'@
gh issue comment 56 --repo $repo --body $issue56Comment
gh issue close 56 --repo $repo --reason completed
```

## Narrow follow-up issues for #57

### 1. Agent onboarding and governance editing workflow

Exact body:

```text
## Goal

Complete the workflow-first “know your Agents” experience without turning the
surface into a generic CRUD table.

## Scope

- Register and edit an Agent.
- Capture Agent Owner, environment, Agent Status, and Risk Level.
- Connect governed Capabilities, Sources, ModelAssets, and Access Grants.
- Show reviewable consequences and links to Runtime Decisions, Human Approval
  Studio, and Evidence & Audit.
- Preserve the existing AGCP Studio shell and workflow-first product direction.
- Append the required Agent, access, and risk-classification audit records.

## Acceptance criteria

- A user can create and edit an Agent through a guided workflow.
- Inventory and grant relationships use real backend records and honest
  empty/error states.
- No fake directory, metrics, compliance score, scanner result, or runtime
  simulation is introduced.
- Backend authorization remains authoritative.
- Tests cover validation, audit events, and the primary browser workflow.

## Non-goals

- No orchestrator behavior.
- No enterprise user/team directory in this issue.
- No automatic AccessGrant/IAM enforcement.
- No legal certification claim.
```

### 2. Guided PolicyCheckStep authoring in Policy Studio

Exact body:

```text
## Goal

Let policy authors persist real metadata-only PolicyCheckSteps from Policy
Studio while preserving the validated IDE layout and deterministic runtime
contract.

## Scope

- Create and update real PolicyCheckStep records.
- Guide check type and target selection.
- Capture required/optional intent, expected safe outcome, failure behavior,
  minimum confidence, status, and evidence retention.
- Keep PolicyVersion check-step snapshots compatible with draft, review, diff,
  activation, and rollback flows.
- Surface resulting CheckResult evidence in Human Approval Studio and Evidence
  & Audit.

## Acceptance criteria

- Authoring remains inside repository / editor / WHEN -> CHECK -> THEN -> PROVE
  / Blocks-Code DSL / compile bar / validation console / inspector.
- Unsupported selectors or check types are rejected, not silently saved.
- Saving a draft does not activate runtime behavior.
- PolicyCheckStep failure_behavior is not silently enforced; decisions change
  only through explicit deterministic PolicyRule matching.
- Tests cover persistence, snapshots, review diff, activation, runtime evidence,
  and browser authoring.

## Non-goals

- No raw-content scanner.
- No arbitrary external tools, code, webhooks, or workflow graph.
- No Publish action or production simulation.
```

### 3. Production-ready Python/LangGraph Runtime Gateway adapter

Exact body:

```text
## Goal

Provide one supported integration boundary that calls AGCP before a governed
tool action and reliably honors the returned Runtime Gateway contract.

## Scope

- Before-tool decision call.
- Mandatory enforcement of proceed.
- Stable idempotency keys.
- Timeout, retry, and failure policy.
- Human review and resume flow.
- Service Actor authentication/scopes.
- Fake-tool integration tests.
- Python package/example documentation, including a LangGraph usage example.

## Acceptance criteria

- deny, require_human_review, and not_applicable never execute the fake tool.
- allow executes exactly once under retry/idempotency tests.
- resume preserves request/run identity and executes only after an allowed
  resume result.
- Timeouts and AGCP failures follow explicit documented behavior.
- Logs and errors never expose API keys, raw prompts, source content, or private
  payloads.

## Non-goals

- No AGCP-side tool execution.
- No replacement for LangGraph or other orchestrators.
- No new runtime decision semantics.
```

### 4. Identity, RBAC, and separation-of-duties hardening

Exact body:

```text
## Goal

Replace local-development human identity assumptions with a real,
auditable authorization foundation for authoring, review, activation, and
evidence access.

## Scope

- Real user identity and session/token boundary.
- Author, reviewer, and activator separation-of-duties rules.
- Enterprise authentication design for OIDC/SAML integration.
- Role-aware frontend behavior backed by authoritative API authorization.
- Audit coverage for grants, denials, review, and activation actions.
- Preserve current Service Actor boundaries.

## Acceptance criteria

- Identity is stable and audit-safe across requests.
- Unauthorized users cannot review, activate, or export evidence.
- Required separation of duties is enforced by the backend, not only disabled
  buttons.
- Frontend shows honest current-actor and denied states.
- Tests cover allowed and denied role combinations.

## Non-goals

- No fake user or team directory.
- No complex generic RBAC framework without a concrete need.
- No legal certification claim.
```

### 5. Clean browser E2E governance flow

Exact body:

```text
## Goal

Prove the main AGCP governance story in a clean, deterministic browser flow
against an isolated PostgreSQL-backed stack.

## Scope

- Start from scripts/validate-clean.ps1 or an equivalent isolated test fixture.
- Cover Agent, Policy draft/review, Runtime Decision, metadata CheckResults,
  HumanApproval, explicit PolicyVersion activation, and Evidence Bundle.
- Verify honest empty/error/disabled states and current-actor behavior.
- Preserve the approved Policy Studio and Human Approval Studio layouts.

## Acceptance criteria

- The test starts from an empty database and applies every migration.
- Runtime metadata pre-check evidence produces CheckResults.
- require_human_review returns proceed=false and creates HumanApproval.
- Policy approval does not activate; activation is explicit.
- Evidence Bundle contains the linked decision/review/check/audit chain.
- No framework overlay or relevant browser console error appears.
- The isolated Compose project and volumes are removed after the run.

## Non-goals

- No fake frontend records.
- No fake production simulation.
- No visual redesign.
```

## Commands to create the five issues

```powershell
$repo = "LIGHTER91/agent-governance-control-plane"

$agentBody = @'
## Goal

Complete the workflow-first “know your Agents” experience without turning the surface into a generic CRUD table.

## Scope

- Register and edit an Agent.
- Capture Agent Owner, environment, Agent Status, and Risk Level.
- Connect governed Capabilities, Sources, ModelAssets, and Access Grants.
- Show reviewable consequences and links to Runtime Decisions, Human Approval Studio, and Evidence & Audit.
- Preserve the existing AGCP Studio shell and workflow-first product direction.
- Append the required Agent, access, and risk-classification audit records.

## Acceptance criteria

- A user can create and edit an Agent through a guided workflow.
- Inventory and grant relationships use real backend records and honest empty/error states.
- No fake directory, metrics, compliance score, scanner result, or runtime simulation is introduced.
- Backend authorization remains authoritative.
- Tests cover validation, audit events, and the primary browser workflow.

## Non-goals

- No orchestrator behavior.
- No enterprise user/team directory in this issue.
- No automatic AccessGrant/IAM enforcement.
- No legal certification claim.
'@
$agentIssue = gh issue create --repo $repo --title "Agent onboarding and governance editing workflow" --body $agentBody

$checkStepBody = @'
## Goal

Let policy authors persist real metadata-only PolicyCheckSteps from Policy Studio while preserving the validated IDE layout and deterministic runtime contract.

## Scope

- Create and update real PolicyCheckStep records.
- Guide check type and target selection.
- Capture required/optional intent, expected safe outcome, failure behavior, minimum confidence, status, and evidence retention.
- Keep PolicyVersion check-step snapshots compatible with draft, review, diff, activation, and rollback flows.
- Surface resulting CheckResult evidence in Human Approval Studio and Evidence & Audit.

## Acceptance criteria

- Authoring remains inside repository / editor / WHEN -> CHECK -> THEN -> PROVE / Blocks-Code DSL / compile bar / validation console / inspector.
- Unsupported selectors or check types are rejected, not silently saved.
- Saving a draft does not activate runtime behavior.
- PolicyCheckStep failure_behavior is not silently enforced; decisions change only through explicit deterministic PolicyRule matching.
- Tests cover persistence, snapshots, review diff, activation, runtime evidence, and browser authoring.

## Non-goals

- No raw-content scanner.
- No arbitrary external tools, code, webhooks, or workflow graph.
- No Publish action or production simulation.
'@
$checkStepIssue = gh issue create --repo $repo --title "Guided PolicyCheckStep authoring in Policy Studio" --body $checkStepBody

$adapterBody = @'
## Goal

Provide one supported integration boundary that calls AGCP before a governed tool action and reliably honors the returned Runtime Gateway contract.

## Scope

- Before-tool decision call.
- Mandatory enforcement of proceed.
- Stable idempotency keys.
- Timeout, retry, and failure policy.
- Human review and resume flow.
- Service Actor authentication/scopes.
- Fake-tool integration tests.
- Python package/example documentation, including a LangGraph usage example.

## Acceptance criteria

- deny, require_human_review, and not_applicable never execute the fake tool.
- allow executes exactly once under retry/idempotency tests.
- resume preserves request/run identity and executes only after an allowed resume result.
- Timeouts and AGCP failures follow explicit documented behavior.
- Logs and errors never expose API keys, raw prompts, source content, or private payloads.

## Non-goals

- No AGCP-side tool execution.
- No replacement for LangGraph or other orchestrators.
- No new runtime decision semantics.
'@
$adapterIssue = gh issue create --repo $repo --title "Production-ready Python/LangGraph Runtime Gateway adapter" --body $adapterBody

$identityBody = @'
## Goal

Replace local-development human identity assumptions with a real, auditable authorization foundation for authoring, review, activation, and evidence access.

## Scope

- Real user identity and session/token boundary.
- Author, reviewer, and activator separation-of-duties rules.
- Enterprise authentication design for OIDC/SAML integration.
- Role-aware frontend behavior backed by authoritative API authorization.
- Audit coverage for grants, denials, review, and activation actions.
- Preserve current Service Actor boundaries.

## Acceptance criteria

- Identity is stable and audit-safe across requests.
- Unauthorized users cannot review, activate, or export evidence.
- Required separation of duties is enforced by the backend, not only disabled buttons.
- Frontend shows honest current-actor and denied states.
- Tests cover allowed and denied role combinations.

## Non-goals

- No fake user or team directory.
- No complex generic RBAC framework without a concrete need.
- No legal certification claim.
'@
$identityIssue = gh issue create --repo $repo --title "Identity, RBAC, and separation-of-duties hardening" --body $identityBody

$e2eBody = @'
## Goal

Prove the main AGCP governance story in a clean, deterministic browser flow against an isolated PostgreSQL-backed stack.

## Scope

- Start from scripts/validate-clean.ps1 or an equivalent isolated test fixture.
- Cover Agent, Policy draft/review, Runtime Decision, metadata CheckResults, HumanApproval, explicit PolicyVersion activation, and Evidence Bundle.
- Verify honest empty/error/disabled states and current-actor behavior.
- Preserve the approved Policy Studio and Human Approval Studio layouts.

## Acceptance criteria

- The test starts from an empty database and applies every migration.
- Runtime metadata pre-check evidence produces CheckResults.
- require_human_review returns proceed=false and creates HumanApproval.
- Policy approval does not activate; activation is explicit.
- Evidence Bundle contains the linked decision/review/check/audit chain.
- No framework overlay or relevant browser console error appears.
- The isolated Compose project and volumes are removed after the run.

## Non-goals

- No fake frontend records.
- No fake production simulation.
- No visual redesign.
'@
$e2eIssue = gh issue create --repo $repo --title "Clean browser E2E governance flow" --body $e2eBody
```

## Issue #57 supersession comment and closure

Exact proposed comment:

> The broad workflow-first frontend rebuild is now largely implemented:
> Overview, Agents and Agent Governance Profile, Policy Studio, Human Approval
> Studio, Runtime Decisions, Evidence & Audit, Access & Data, and Integration
> Hub are backend-connected or intentionally bounded. Policy Studio and Human
> Approval Studio preserve the approved AGCP Studio layouts; the remaining
> work is narrower than this umbrella issue.
>
> Follow-up issues:
>
> - Agent onboarding and governance editing workflow: `$agentIssue`
> - Guided PolicyCheckStep authoring in Policy Studio: `$checkStepIssue`
> - Production-ready Python/LangGraph Runtime Gateway adapter: `$adapterIssue`
> - Identity, RBAC, and separation-of-duties hardening: `$identityIssue`
> - Clean browser E2E governance flow: `$e2eIssue`
>
> Closing #57 as superseded by these focused, testable tasks. This does not
> claim production or enterprise readiness.

Commands, run in the same PowerShell session that created the issues:

```powershell
$issue57Comment = @"
The broad workflow-first frontend rebuild is now largely implemented: Overview, Agents and Agent Governance Profile, Policy Studio, Human Approval Studio, Runtime Decisions, Evidence & Audit, Access & Data, and Integration Hub are backend-connected or intentionally bounded. Policy Studio and Human Approval Studio preserve the approved AGCP Studio layouts; the remaining work is narrower than this umbrella issue.

Follow-up issues:

- Agent onboarding and governance editing workflow: $agentIssue
- Guided PolicyCheckStep authoring in Policy Studio: $checkStepIssue
- Production-ready Python/LangGraph Runtime Gateway adapter: $adapterIssue
- Identity, RBAC, and separation-of-duties hardening: $identityIssue
- Clean browser E2E governance flow: $e2eIssue

Closing #57 as superseded by these focused, testable tasks. This does not claim production or enterprise readiness.
"@
gh issue comment 57 --repo $repo --body $issue57Comment
gh issue close 57 --repo $repo --reason completed
```
