# Frontend Product Blueprint

Status: current local V1 product direction for AGCP frontend work. AGCP is an
advanced product prototype, not a production- or enterprise-ready frontend.
This document is a blueprint, not a new implementation plan for redesigning
existing validated screens.

## Product Positioning In UI

AGCP is an Agent Governance Control Plane. It helps teams govern agents that
run in other runtimes and orchestrators. The frontend should consistently make
three product promises:

- Know which agents exist, who owns them, and what they can access.
- Control risky actions through policy decisions, reviews, and explicit
  activation flows.
- Prove what happened through audit trails, PolicyDecisions, CheckResults,
  HumanApprovals, and Evidence Bundles.

AGCP is not an orchestrator. The UI must not imply that AGCP executes tools,
runs LangGraph/n8n/Dataiku workflows, or replaces the caller runtime. The
caller/orchestrator remains responsible for honoring Runtime Gateway decisions.

AGCP is not a legal certification product. The UI may describe evidence,
review status, control coverage, and audit export. It must not claim legal
compliance, certification, compliance scores, or guaranteed safety.

## UX Principle

The AGCP frontend is workflow-first, not backend-resource-first.

Screens should be organized around user jobs: reviewing an agent, authoring a
policy, approving a runtime action, inspecting evidence, or preparing an
integration. They should not directly mirror database tables, enum lists, or
raw API endpoints unless the requested feature is explicitly an admin/debug
surface.

Backend resource shapes still matter, but they should be translated into
product concepts:

- Policy and PolicyRule become Policy Studio authoring surfaces.
- HumanApproval and PolicyVersionReviewRequest become Review Inbox work items.
- PolicyDecision, CheckResult, AuditLog, and TraceEvent become evidence chain
  context.
- AccessGrant, Source, DataUsageProfile, Capability, and ModelAsset become
  access and inventory governance context.

## Site Map And Navigation

| Surface | User Job | Current State | Remaining Gaps | What Not To Build |
| --- | --- | --- | --- | --- |
| Overview | Enter the product, see real operating status, and move to key workflows. | Root page is a connected product narrative for know/control/prove. It reads current actor, Agent, review, Policy, and Runtime activity endpoints and uses honest unavailable/empty states instead of synthetic metrics. | Deeper evidence and operating summaries only when stable backend read models justify them. | Do not add fake charts, compliance scores, or production metrics. |
| Agents | Understand registered agents, owners, risk, environment, activity, approvals, and evidence. | Agent list and detail routes are backend-connected and use AGCP Studio visual language. Agent detail includes profile, activity, approvals, and evidence actions. | Agent onboarding/editing, stronger filtering, inventory relationships, and deeper runtime drill-down. | Do not turn this into a generic Agent CRUD table. |
| Policy Studio | Author, inspect, validate, and prepare governance policies. | Implemented as an IDE-like surface with honest Local backend / Policy repository labels, backend-backed policy folders, compact folder create/rename/delete-empty/move controls, repository sidebar, center editor, editable Blocks canvas and Code DSL toggle, `WHEN -> CHECK -> THEN -> PROVE`, local validation, inspector, draft snapshots, review submit, activation-gated flow, archive, and draft-only delete. | Backend-backed repository/workspace metadata if the domain model adds it, PolicyCheckStep authoring UI, explicit operator persistence, richer version history, and focused review workflow refinements. | Do not reintroduce generic Policy/PolicyRule CRUD forms, Publish, fake repositories/workspaces, fake simulations, or fake impact metrics. |
| Access & Data | Review declared agent access, source usage metadata, model/capability inventory, and metadata-only check readiness. | Workflow-first Access & Data page is backend-connected to Access Grants, Sources, DataUsageProfiles, Models, and Capabilities. It shows boundary copy, real empty/error/loading states, safe metadata summaries, Access Grant lifecycle transitions, readiness for supported metadata-only check inputs, and a local demo callout that creates real backend evidence. | Deeper cross-links to Agent Governance Profile, policy check step authoring, review workflows, and Evidence Bundle context once the backend read models need it. | Do not imply Access Grants are IAM credentials or automatic runtime enforcement. Do not expose raw source content, prompts, secrets, tokens, credentials, fake scanner output, legal certification, or production simulations. |
| Runtime Decisions | Understand Runtime Gateway decisions and runtime activity. | Implemented as a workflow-first timeline over real Runtime Gateway activity, including request/context, active PolicyVersion or fallback state, metadata-check state, HumanApproval linkage, and Evidence Bundle navigation. | Richer detail, filtering, pagination, and direct CheckResult drill-down where backend read models support them. | Do not make AGCP execute tools or become a runtime/orchestrator. |
| Reviews | Resolve runtime HumanApprovals and PolicyVersion review requests. | Human Approval Studio implements the attached review-inbox mockup inside the existing shell, with unified work items, Mine / Waiting / Approved / Completed lanes, a left Review Inbox queue, center selected review detail, right current actor / assign / actions rail, policy decision context, checks, evidence preview, approve/reject, and explicit activation when applicable. | Request-info, runtime assignment, notifications, richer assignment, and enterprise identity integration. | Do not make reviews backend resource tables or add a fake reviewer directory. |
| Evidence & Audit | Export and inspect bounded evidence for review. | Implemented as a consolidated workflow-first explorer that manually loads one real Evidence Bundle and organizes Subject, Policy Decision, CheckResults, Human Review, Policy Review, Audit Trail, and bounded JSON export. | General evidence/audit listing, filtering, PDF/signature/archive design, retention, and external export. | Do not expose raw prompts, source contents, secrets, tokens, fake scanner results, or legal certification claims. |
| Integrations | Understand how external runtimes connect to AGCP without AGCP orchestrating them. | Integration Hub explains Runtime Gateway API, LangGraph, n8n, Dataiku, MCP, generic webhooks, Service Actor expectations, modes, and boundaries. | Adapter packages, stronger auth, setup validation, and production integration guides. | Do not build a workflow orchestrator or claim design-only integrations are production-ready. |
| Settings/Admin | Configure local/dev actor behavior and, later, admin surfaces. | Local admin actor support and read-only service actor concepts exist where enabled. Settings remains lightweight. | Enterprise auth, user/team/org administration, service actor key rotation, and production operations. | Do not add fake enterprise auth, fake users, or plaintext API key display. |

## Current Validated Surfaces

### Policy Studio

Policy Studio is the validated direction for policy authoring. It must remain an
IDE-like product surface, not a CRUD admin page.

Validated structure:

- Repository-style policy sidebar.
- Honest Local backend / Policy repository state until backend repository or
  workspace concepts exist.
- Backend-backed Policy folders, with uncategorized Policies represented by a
  null `folder_id` rather than fake folder metadata.
- No route-local navigation rail; the Policy Studio IDE layout lives within the
  existing app shell.
- Center editor.
- `WHEN -> CHECK -> THEN -> PROVE` policy structure bar.
- Blocks and Code DSL toggle.
- Editable compact Blocks canvas for supported V1 condition fields, with
  consistent icons and visible section connectors.
- Code DSL as the precise escape hatch for supported deterministic condition
  JSON.
- Compile bar.
- Local validation console.
- Right inspector.
- Draft, review, approval, activation, rollback-draft, archive, and draft-only
  delete governance flows where backend support exists.

Validated behavior:

- Save draft persists a draft PolicyVersion snapshot.
- Submit for review creates a PolicyVersionReviewRequest for the saved draft.
- Pending review locks the draft content and requires a new draft for changes.
- Approval or rejection records reviewer intent and does not activate runtime
  behavior.
- Activation is explicit and is not called Publish.
- There is no direct Publish button by design.
- Local validation is parser/compile validation only, not runtime simulation.
- Templates are authoring helpers, not backend records.
- Policy folders are backend-backed through PolicyFolder records and Policy
  `folder_id`. Creating, renaming, listing, moving, and deleting empty folders
  must use the API. Deleting a non-empty folder is blocked until Policies are
  moved elsewhere.
- Repository rows use product labels first and keep backend references as short
  technical refs, not primary row titles.
- Blocks mode remains the primary visual authoring surface. The Code DSL is the
  precise escape hatch and the validation console reports local parser/compiler
  state only.
- Repository tags, owners, and version rows must be backend-backed or explicitly
  local/empty. If the backend lacks metadata for a category, Policy Studio
  should group persisted records honestly instead of showing mock categories or
  fake tag chips.
- The frontend must not invent Policy repositories, workspaces, folders, sync
  state, versions, validation errors, or tags. Search and refresh are allowed
  only when wired to real backend list behavior.

Future Policy Studio work must preserve the existing AGCPStudio layout and
product direction unless a human explicitly requests a redesign.

### Human Approval Studio

Human Approval Studio is the validated business surface direction for runtime
and policy review work. The attached Human Approval Studio mockup is the source
of truth for this surface. It lives inside the existing AGCP Studio shell and
uses the same compact rail-only sidebar pattern as Policy Studio; the topbar and
global shell styling are not redesigned by this surface. It must remain a
review workflow, not a backend table browser.

Validated structure:

- Internal breadcrumb: Governance / Human Approval Studio.
- Left Review Inbox queue of work items with Mine, Waiting, Approved, and
  Completed lanes.
- Center selected review detail for the selected review.
- Right current actor / assign reviewer / actions / request info rail.
- "Why Review Is Required" context.
- Runtime Decision and Policy Review context.
- Policy Checks and metadata-only CheckResult evidence.
- Evidence Preview.
- Action row for approve, reject, request info, reassign, and explicit
  activation when applicable.

Validated behavior:

- Runtime HumanApproval work items are reviewable without faking runtime
  enforcement.
- PolicyVersionReviewRequest work items can be assigned, approved, rejected,
  and explicitly activated when approved.
- Approval does not activate automatically.
- Activation changes future runtime evaluation only through the explicit
  activation endpoint.
- Current actor state is visible and frontend role-aware behavior is advisory.
- Backend authorization remains authoritative.
- Request-info and escalation flows are represented honestly as not wired yet.
- There is no fake reviewer directory.

## Policy Studio Wireflow

1. User selects or creates a policy in the repository sidebar.
2. User edits policy intent in the Blocks canvas or Code DSL.
3. User clicks Validate to run local parser/compile checks.
4. User clicks Save draft to persist a draft PolicyVersion snapshot.
5. User clicks Submit for review only after a valid saved draft exists.
6. Pending review locks the draft from mutation.
7. Reviewer approves or rejects in Review Inbox.
8. Approval does not activate the version.
9. A user explicitly activates an approved review request.
10. Runtime behavior changes only after activation.
11. Future changes require creating a new draft.
12. Prior versions can create rollback drafts, but rollback drafts also require
    review and explicit activation.
13. Archive keeps evidence/history.
14. Delete is limited to draft-only policies with no governance history.

No Publish action exists by design. If future product copy needs a runtime
change verb, prefer explicit activation language.

## Human Approval Studio Wireflow

Human Approval Studio handles two related review streams:

- Runtime HumanApproval records created by Runtime Gateway decisions.
- PolicyVersionReviewRequest records created by Policy Studio Submit for
  review.

Runtime review flow:

1. Runtime Gateway returns a decision that requires human review.
2. HumanApproval is created.
3. Human Approval Studio shows the request with policy decision context, check
   evidence, and safe metadata.
4. Reviewer approves, rejects, or cancels according to backend rules.
5. Any caller-side resume remains explicit and outside AGCP tool execution.

Policy version review flow:

1. Policy Studio submits a saved draft PolicyVersion.
2. Human Approval Studio shows the review request.
3. Reviewer can inspect diff, evidence, assignment, current actor, and status.
4. Reviewer approves or rejects.
5. Approved review can be activated explicitly.
6. Activation changes future Runtime Gateway and telemetry evaluation only when
   the backend activation endpoint succeeds.

Unsupported V1 behaviors must remain explicit:

- Escalation is not wired yet.
- Request-info is not wired yet.
- Notifications and email are not implemented.
- Reviewer directory and enterprise identity are not implemented.

## Evidence And CheckResult Flow

Runtime Gateway can produce PolicyDecision records. Metadata-only pre-checks can
produce CheckResults when the explicit feature flag is enabled and authored
PolicyCheckSteps are active.

Evidence surfaces should show safe summaries:

- PolicyDecision.
- Active PolicyVersion reference where available.
- CheckResult summaries: check type, outcome, target, confidence, timestamp,
  and filtered safe metadata.
- HumanApproval records.
- TraceEvents.
- AuditLogs.
- AccessGrant, Source, Capability, ModelAsset, and DataUsageProfile references
  where safe.

Evidence surfaces must not expose:

- Raw prompts.
- Raw source content or chunks.
- Secrets, tokens, credentials, or API keys.
- Unsafe runtime payloads.
- Fake scanner results.
- Legal certification claims.

The Evidence Bundle JSON remains the canonical bounded export until PDF,
signing, and archive formats are designed separately.

## Remaining Frontend Gaps

- Overview: is connected and useful; deeper summaries should wait for stable
  backend evidence/read models rather than synthetic metrics.
- Agents: needs onboarding/edit flows, filtering, and deeper relationships to
  inventory, policy versions, runtime decisions, reviews, and evidence.
- Access & Data: now has a workflow-first metadata review surface across
  Sources, DataUsageProfiles, AccessGrants, Capabilities, ModelAssets, related
  governance workflows, and metadata check readiness. Remaining gaps are deeper
  Agent/profile/evidence drill-downs and future PolicyCheckStep authoring once
  the product flow is designed.
- Runtime Decisions: needs a better timeline and decision detail workspace with
  policy version, checks, approvals, and evidence links.
- Evidence & Audit: is consolidated for the bounded one-Agent JSON workflow.
  Remaining gaps are a general evidence/audit index, filtering,
  PDF/signature/archive packaging, retention, and external export.
- Integrations: needs real adapter package work only after auth, caller
  enforcement, and packaging boundaries are designed.
- Settings/Admin: needs local actor clarity now and enterprise auth/admin later,
  without fake users or fake role directories.
- Demo UX: the one-command metadata pre-check path exists and creates real
  backend evidence. Remaining work is clean browser/E2E validation of that
  workflow, not hardcoded frontend demo data.

## Anti-Patterns

Do not build:

- API-shaped CRUD screens as the primary product experience.
- Giant primary tables where a workflow surface is needed.
- Enum dumps as UX.
- Fake production metrics.
- Fake compliance scores.
- Fake runtime simulations.
- Fake scanner results.
- Fake reviewer directories.
- Publish buttons or publish-like wording for policy activation.
- AGCP-side tool execution.
- Frontend changes that replace the validated AGCPStudio UX without explicit
  approval.

## Relationship With AGENTS.md

This blueprint operationalizes the frontend product UX rules in `AGENTS.md`.
Future frontend work should preserve the validated AGCPStudio direction, stay
workflow-first, avoid legal/compliance claims, avoid fake data, and keep AGCP
positioned as a governance and evidence control plane rather than an
orchestrator.
