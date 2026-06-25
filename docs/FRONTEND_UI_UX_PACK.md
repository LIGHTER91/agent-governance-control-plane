# Frontend UI/UX Pack

Status: desktop-first product design pack for AGCP frontend planning.

This pack prepares the next frontend surfaces for the Agent Governance Control
Plane. It does not replace the existing `FRONTEND_PRODUCT_BLUEPRINT.md`; it
turns that blueprint into desktop UI/UX surfaces that can be implemented in
small, product-safe steps.

## Scope

The frontend is desktop-first. No mobile app or mobile-optimized layout is in
scope for this pack.

Minimum supported viewport should be treated as an explicit product constraint,
not an accidental failure mode:

- target working canvas: 1440 x 900;
- minimum supported width: 1180 px;
- below the minimum, show a compact unsupported-viewport message or preserve a
  desktop canvas with intentional horizontal overflow;
- do not spend product effort on mobile navigation, mobile drawers, or
  phone-sized editing flows.

## Visual Concepts

These generated concepts are directional references, not implementation-ready
specs. Before coding from one of them, review the visible copy and remove any
unapproved action such as creating an Agent if the backend workflow is not in
scope.

- [Agent 360 concept](assets/frontend-ui-ux-pack/agent-360-concept.png)
- [Decision Review Desk concept](assets/frontend-ui-ux-pack/decision-review-desk-concept.png)
- [Evidence & Audit Workbench concept](assets/frontend-ui-ux-pack/evidence-audit-workbench-concept.png)
- [Policy Studio Refinement concept](assets/frontend-ui-ux-pack/policy-studio-refinement-concept.png)
- [Policy Studio Code DSL concept](assets/frontend-ui-ux-pack/policy-studio-code-dsl-concept.png)
- [Access & Inventory Matrix concept](assets/frontend-ui-ux-pack/access-inventory-matrix-concept.png)
- [Runtime Decision Trace concept](assets/frontend-ui-ux-pack/runtime-decision-trace-concept.png)
- [Integration Readiness Center concept](assets/frontend-ui-ux-pack/integration-readiness-center-concept.png)

## Mockup Set

| Window | Theme | Design intent |
| --- | --- | --- |
| Agent 360 | Agent governance dossier | Make ownership, allowed access, recent decisions, and evidence visible in one workspace. |
| Decision Review Desk | Human oversight inbox | Help reviewers understand why a decision or PolicyVersion needs review before taking action. |
| Evidence & Audit Workbench | Evidence chain and bounded export | Show what records are included, excluded, and exportable without exposing unsafe raw data. |
| Policy Studio Refinement | Deterministic policy IDE | Preserve the `WHEN -> CHECK -> THEN -> PROVE` authoring flow with Blocks and Code DSL variants, local validation, and review gating. |
| Access & Inventory Matrix | Declared access inventory | Compare Agent access declarations across Tools, Models, Data Sources, and external targets. |
| Runtime Decision Trace | Request-to-decision trace | Explain the evaluation path for a runtime request without implying workflow execution. |
| Integration Readiness Center | External runtime connection | Help teams connect runtimes safely while keeping AGCP as the governance control plane. |

## Product UI Principles

AGCP screens should answer governance questions, not expose database tables.

Every primary surface should help answer at least one of these:

- Which Agents exist?
- Who owns them?
- What are they allowed to do?
- Which Tools, Models, and Data Sources can they access?
- What did they actually do?
- Which Policy allowed, denied, or escalated the action?
- Who approved the Agent, Policy, exception, or Human Approval?
- What Evidence Bundle can be exported for review or audit?

Boundaries:

- AGCP is not an orchestrator.
- AGCP does not execute tools or run external workflows.
- Runtime callers remain responsible for honoring decisions.
- Evidence supports review and audit workflows; it is not legal
  certification.
- Do not use numeric trust, maturity, legal certification, or risk-ranking
  metrics.
- Do not add fake production simulation, fake scanner results, fake users, or
  fake reviewer directories.

## Shared Desktop Shell

The current AGCP Studio shell direction should remain: dense, operational,
dark-neutral, and workflow-oriented.

Recommended desktop shell:

- left navigation rail grouped by workflow, not by API resource;
- compact topbar with breadcrumb and only route-relevant actions;
- no global Search button unless it opens a real command/search surface;
- no global Simulation toggle unless the active screen has a real local
  validation or preview mode;
- environment / enforcement indicators must come from real backend state or use
  cautious copy such as "local development mode";
- disabled future nav items should state "planned" or be hidden until useful.

Desktop layout rule:

- use fixed rails and panes where they support operator speed;
- use split panes for master/detail work;
- use timelines and evidence chains for audit context;
- use tables only when comparison across records is the main task;
- avoid generic CRUD forms as the main product experience.

## Surface 1: Agent 360

Primary job: inspect one Agent as a governance object.

Primary route candidates:

- `/agents`
- `/agents/[agentId]`

Layout:

- left: searchable Agent list with filters for Environment, Agent Owner, Agent
  Status, and Risk Level;
- center: selected Agent summary with owner, lifecycle state, framework,
  declared access, recent Agent Runs, and recent Policy Decisions;
- right: governance inspector with Human Approval state, Evidence Bundle
  action, Audit Log trail, related Policies, and open review items.

Key components:

- Agent list row;
- Agent status header;
- ownership panel;
- Allowed Access table grouped by Tool, Model, Data Source, and external target;
- Recent Decisions timeline;
- Evidence Bundle summary;
- Audit Log mini timeline.

Important copy:

- "Who owns this Agent?"
- "Allowed access"
- "Recent decisions"
- "Human oversight"
- "Evidence bundle"

Do not build:

- a generic Agent create/edit CRUD workflow as the first screen;
- synthetic charts;
- fake production totals;
- broad relationship graphs before the list/detail workflow is strong.

Acceptance criteria:

- the screen makes ownership, allowed access, recent decisions, and evidence
  availability visible without opening four separate pages;
- empty backend states are honest;
- all links drill into real Agent, Policy Decision, Human Approval, or Evidence
  routes.

## Surface 2: Decision Review Desk

Primary job: resolve runtime and PolicyVersion review work in one place.

Primary route candidate:

- `/human-approvals`

Layout:

- left: review queue grouped by Mine, Waiting, Escalated, Completed;
- center: selected review detail with why review is required, Policy Decision,
  Policy Rule, CheckResults, Data Source context, Model context, and reviewer
  note;
- right: inspector with active PolicyVersion, related Agent, Evidence Bundle,
  Audit trail, and actions.

Key components:

- Review queue item;
- work item status tabs;
- selected review detail;
- CheckResult cards;
- Policy Decision summary;
- Evidence preview;
- reviewer note field;
- action bar.

Allowed actions:

- Approve;
- Reject;
- Request info, only when backend support exists;
- Reassign, using explicit actor id until identity integration exists;
- Activate approved version, only for approved PolicyVersion reviews.

Important copy:

- "Backend authorization still enforced"
- "Approval does not activate this version"
- "Activation changes future runtime policy evaluation"
- "No fake reviewer directory"

Do not build:

- a table-first HumanApproval admin page;
- automatic resume wording;
- fake escalation routing;
- fake people picker;
- publish-like Policy wording.

Acceptance criteria:

- a reviewer can understand why a decision needs review before approving;
- runtime HumanApprovals and PolicyVersion reviews feel related but distinct;
- activation remains explicit and separate from approval.

## Surface 3: Evidence & Audit Workbench

Primary job: inspect and export bounded evidence.

Primary route candidates:

- `/evidence`
- future `/audit`

Layout:

- left: filter rail for Agent, Environment, Policy Decision, Human Approval
  status, and date range;
- center: evidence chain timeline for one selected Agent Run or Policy
  Decision;
- right: export and metadata inspector.

Evidence chain steps:

- Agent;
- Agent Run;
- Trace Events;
- Policy Decisions;
- CheckResults;
- Human Approval;
- Audit Logs;
- Evidence Bundle.

Key components:

- evidence chain row;
- safe metadata viewer;
- included record counts;
- export warning panel;
- bounded JSON export action;
- missing evidence state;
- audit event timeline.

Important copy:

- "Safe metadata only"
- "Bounded export"
- "Evidence chain"
- "Audit trail"
- "Create evidence bundle"

Do not build:

- raw prompt display;
- raw source content display;
- secret/token/credential fields;
- legal certification wording;
- PDF or signing UI unless that workflow is actually designed and implemented.

Acceptance criteria:

- reviewers can see which records are included and which are intentionally
  excluded;
- export action is manual and auditable;
- evidence remains bounded JSON until a separate export format is designed.

## Surface 4: Policy Studio Refinement

Primary job: author, validate, review, and activate deterministic policy
inputs.

Primary route:

- `/policies`

Keep the validated structure:

- repository sidebar;
- center editor;
- policy structure bar using `WHEN -> CHECK -> THEN -> PROVE`;
- Blocks / Code DSL toggle;
- compact block list;
- compile bar;
- local validation console;
- right inspector.

Desktop refinements:

- keep the IDE layout, but set a real minimum width;
- prevent structure bar and validation console clipping at desktop sizes;
- replace inert global Simulation with route-local "Local validation";
- make Code DSL the precise authoring mode;
- make Blocks mode a readable projection until full bidirectional editing is
  designed.

Do not build:

- generic Policy / PolicyRule CRUD forms;
- direct Publish action;
- production simulation;
- policy impact metrics;
- legal-compliance labels.

Acceptance criteria:

- Save draft persists a draft PolicyVersion snapshot;
- Submit for review only appears when a saved draft can be reviewed;
- pending review locks the draft;
- approved review requires explicit activation;
- local validation is clearly not runtime simulation.

## Surface 5: Access & Inventory Matrix

Primary job: understand what Agents are allowed to access and what evidence
supports that access.

Primary route candidate:

- `/access-data`

Layout:

- left: inventory filters by Agent, Tool, Model, Data Source, Access Grant
  status, and Data Usage Profile review status;
- center: access matrix with rows for Agents and columns grouped by Tool,
  Model, Data Source, and external target;
- right: selected Access Grant or Source/Data Usage Profile inspector.

Key components:

- Access Grant lifecycle row;
- Source profile panel;
- Data Usage Profile summary;
- related Agent links;
- evidence reference links;
- status transition action group.

Do not build:

- IAM permission management;
- credential display;
- automatic runtime enforcement claims;
- legal-use certification.

Acceptance criteria:

- Access Grants are clearly declarations, not credentials;
- Data Usage Profiles are governance metadata, not legal truth;
- each status transition explains its audit/runtime boundary.

## Surface 6: Runtime Decision Trace

Primary job: understand how AGCP evaluated a runtime request.

Primary route candidate:

- `/runtime-gateway`

Layout:

- left: filterable runtime activity list;
- center: request-to-decision timeline;
- right: active policy/version/check/evidence inspector.

Trace stages:

- request received;
- Agent context resolved;
- Access/Data/Model context resolved;
- metadata CheckResults recorded when available;
- Policy evaluated;
- Human Approval requested when needed;
- Evidence Bundle available when exported.

Do not build:

- tool execution controls;
- workflow resume automation;
- production simulation;
- fake live traffic.

Acceptance criteria:

- the UI explains `proceed=true/false` without implying AGCP runs the tool;
- PolicyDecision and Evidence Bundle links are first-class;
- missing CheckResults are shown as unavailable, not invented.

## Surface 7: Integration Readiness Center

Primary job: help teams connect external runtimes to AGCP safely.

Primary route candidate:

- `/integrations`

Layout:

- left: integration pattern list: Custom Runtime Gateway API, LangGraph,
  n8n, Dataiku, MCP gateway/control pattern, generic webhook/API;
- center: selected integration setup, boundaries, required scopes, and event
  examples;
- right: Service Actor registry and key metadata when enabled.

Do not build:

- adapter marketplace claims;
- workflow execution;
- plaintext API key display;
- fake connected state for design-only integrations.

Acceptance criteria:

- every integration states whether it is connected, design-only, spike, or not
  configured;
- callers remain responsible for respecting AGCP decisions;
- Service Actor key metadata never exposes secret values or hashes.

## Component System

Shared primitives should be extracted from the current AGCP Studio shell before
the next major frontend build:

- AppShell;
- SidebarNav;
- Topbar;
- WorkspacePane;
- InspectorPane;
- StatusBadge;
- SemanticPill;
- Timeline;
- EvidenceChain;
- DataTable;
- FilterRail;
- ActionBar;
- EmptyState;
- ErrorState;
- SafeMetadataViewer.

Design token direction:

- background: dark neutral, not pure black;
- panels: slightly lifted dark surfaces with subtle borders;
- text: high-contrast headings, muted body labels;
- accent: restrained violet for focus and selection only;
- semantic colors: emerald for allowed/pass/active, amber for review/warning,
  red for deny/fail/critical;
- radius: compact, mostly 6-10 px;
- density: desktop operator density, not marketing spacing;
- typography: deliberate mono for IDs, endpoints, and technical references;
  sans-serif for product copy and labels.

## Implementation Sequence

1. Shell cleanup.
   Extract shell, nav, topbar, tokens, and primitives from `AGCPStudio.tsx`.
   Keep desktop min-width explicit.

2. Policy Studio hardening.
   Fix desktop clipping, remove inert global mode ambiguity, and keep the IDE
   layout stable.

3. Agent 360.
   Upgrade Agent list/detail into a single stronger governance workspace.

4. Decision Review Desk.
   Continue from the current Review Inbox direction and deepen selected review
   context.

5. Evidence & Audit Workbench.
   Consolidate evidence chain, safe metadata, export warnings, and bounded JSON
   actions.

6. Access & Inventory Matrix.
   Improve cross-linking among Agents, Access Grants, Sources, Data Usage
   Profiles, Capabilities, Models, Policies, and Evidence.

7. Integration Readiness Center.
   Keep integration setup reviewable without turning AGCP into an orchestrator.

## Global Acceptance Checklist

Before marking any frontend surface complete:

- desktop viewport verified at 1440 x 900 or equivalent;
- no mobile layout promised;
- no framework error overlay;
- no console errors from the app;
- main workflow interaction tested;
- empty, loading, error, and ready states reviewed;
- all visible copy respects AGCP boundaries;
- no secrets or unsafe metadata rendered;
- no fake metrics, fake users, fake production simulation, or legal
  certification claims;
- relevant backend API behavior documented in the page or route README when
  needed;
- screenshots or browser notes confirm layout preservation.
