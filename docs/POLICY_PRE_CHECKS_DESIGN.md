# Policy Pre-Checks And Control Tools Design

## Status

Design plus first backend foundation. `CheckTool` and `CheckResult`
persistence, Pydantic create/read schemas, a minimal internal helper for
persisting CheckResults, internal metadata-only check helpers, and a formal
adapter boundary in `agent_governance_api.check_tools` now exist. The adapter
boundary defines safe request/result types, execution modes, a protocol for
future adapters, and a metadata-only adapter for AccessGrant status, Data Usage
Profile review status, Source status/classification, ModelAsset status/provider
type, and Capability status. Runtime Gateway can optionally execute active
authored PolicyCheckSteps linked to matched PolicyRules behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true` through that metadata-only
adapter boundary and persist linked CheckResults without changing the final
decision automatically. Persistent PolicyCheckStep check types now include
`source_classification` and `model_provider_type`, so authored runtime
pre-checks can request these safe metadata lookups without scanner integration
or raw content inspection. PolicyRules can now explicitly match safe
CheckResult outcome context through deterministic `check_*` fields. Scanner
integrations, external integrations, automatic CheckResult-driven enforcement,
public CheckTool/CheckResult management APIs, and frontend UI remain out of
scope.

Policy versioning and review guardrails are designed separately in
`docs/POLICY_VERSIONING_REVIEW_DESIGN.md`. PolicyCheckStep authoring should
eventually be governed by that lifecycle because check steps can affect which
evidence is collected for future Runtime Gateway decisions.

AGCP remains a governance and evidence control plane. It does not execute
arbitrary tools, orchestrate workflows, replace DLP or data catalog systems, act
as a DPO or legal counsel, or certify legal compliance.

## Critical Assessment

Policy Pre-Checks are useful for AGCP because static policy evaluation is often
insufficient for data-sensitive runtime actions. Before allowing an Agent to
vectorize a Source with an external embedding model, AGCP may need safe facts
about Source classification, personal or sensitive data signals, Data Usage
Profile review state, AccessGrant status, model provider approval, and DPIA
references.

Pre-checks differ from policy evaluation itself. A check gathers or verifies a
bounded fact, such as "does this Agent have an active AccessGrant for this
Source?" or "does the Source profile prohibit embedding?" Policy evaluation
uses those check outcomes to make a deterministic decision such as allow, deny,
or require human review.

Pre-checks also differ from orchestration. AGCP should not retrieve documents,
run agent workflows, call arbitrary business tools, or perform long-running
data processing in the Runtime Gateway path. A check should be a governed
control input with a constrained interface, safe outputs, and evidence
references. Long or expensive scans should be async, precomputed, or delegated
to external systems and represented through safe summaries.

Main risks:

- turning AGCP into a workflow engine by letting PolicyRules run arbitrary
  check graphs;
- adding latency or outages by running expensive scans synchronously in runtime
  enforcement;
- storing raw source chunks, prompts, secrets, credentials, or scanner payloads;
- over-trusting scanner or catalog results as legal truth;
- hiding important governance uncertainty behind a simple allow decision.

The safe path is to start with metadata-only checks over AGCP inventory,
Data Usage Profile, AccessGrant, ModelAsset, Capability, and HumanApproval
state. External check adapters can come later, after runtime context and
Data Usage Profile persistence exist.

Issue #61 should be treated as an adapter-boundary milestone, not a scanner
integration milestone. The useful V1 work is to define what a CheckTool adapter
may receive, what it may return, and how those outputs can become safe
CheckResult evidence. That prepares future catalog, DLP, PII, and scanner
integrations without adding arbitrary network calls, webhooks, raw payload
storage, or runtime orchestration today.

## Problem Statement

Static PolicyRules that match only request fields cannot always answer
data-sensitive governance questions. For example:

```text
Agent RAG requests vectorization of a Source using an external embedding model.
```

The final decision may depend on several checks:

- Source classification;
- PII or sensitive data indicators;
- Data Usage Profile allowed and prohibited purposes;
- active AccessGrant for the Source, ModelAsset, and Capability;
- model provider approval or risk classification;
- DPO review status;
- DPIA requirement and reference;
- owner approval or HumanApproval state.

Those checks should be explicit, auditable, safe, and deterministic enough to
support PolicyDecision evidence. They should not require AGCP to store raw data
or execute arbitrary workflows.

## Concepts

### CheckTool

A registered control capability that can produce a safe check result.

Examples:

- `data_catalog_lookup`;
- `pii_detector`;
- `dlp_classifier`;
- `secret_scanner`;
- `legal_usage_profile_checker`;
- `access_grant_checker`;
- `model_provider_risk_checker`;
- `anonymization_checker`;
- `owner_approval_checker`.

V1 starts with internal metadata-only CheckTools that read existing AGCP
records. The persistence foundation records the registry entry for such a
tool; it does not execute arbitrary tools. External CheckTools should be
adapters with strict input/output contracts, not arbitrary executable code.

The backend now includes a small `CheckToolAdapter` protocol and
`MetadataOnlyCheckToolAdapter` in `agent_governance_api.check_tools`. This is a
code boundary rather than a public API. It allows tests and future services to
construct safe `CheckToolRequest` values and receive safe `CheckToolResult`
values before deciding whether to persist them as `CheckResult` records.

### Adapter Safe Input

A `CheckToolRequest` may contain only safe identifiers and bounded metadata:

- `agent_id`, `run_id`, `request_id`, and `trace_event_id`;
- `policy_decision_id`, `policy_version_id`, `policy_rule_id`, and
  `policy_check_step_id`;
- `check_type`;
- `target_type` and `target_id`;
- `source_id`, `model_id`, and `capability_id`;
- `purpose` and declared `data_classification`;
- safe declared metadata and resolved inventory metadata after metadata safety
  filtering.

The request must not contain raw prompts, raw source contents, chunks,
credentials, API keys, tokens, private payloads, arbitrary user code, arbitrary
external URLs, executable arguments, or scanner raw findings.

### Adapter Safe Output

A `CheckToolResult` may contain:

- `check_type`;
- safe `target_type` and `target_id`;
- bounded `outcome`;
- bounded `confidence`;
- redacted `summary` and `reason`;
- safe scalar metadata such as status labels, provider labels,
  classification labels, evidence references, and policy/version references.

It must not contain raw content, raw prompts, credentials, scanner payloads,
detected secret values, or private customer data. When converted to a
CheckResult payload, PolicyVersion and PolicyCheckStep references remain safe
metadata unless the CheckResult schema later gains explicit columns.

### Implemented Metadata-only Adapter Checks

The first adapter supports these local DB metadata checks only:

- `access_grant_status`;
- `data_usage_profile_status`;
- `source_status`;
- `source_classification`;
- `model_asset_status`;
- `model_provider_type`;
- `capability_status`.

They do not call external systems and do not inspect source content. Missing
context returns `not_applicable`; missing inventory generally returns
`unknown`; inactive, expired, disabled, revoked, or rejected states return
`fail` where the domain status is conclusive. Classification and provider type
checks report available metadata, not approval or legal determinations.

### PolicyCheckStep

A policy-associated requirement to run one CheckTool against a bounded part of
the contextual runtime request.

Example:

```text
For action_type = vectorize and model.provider_type = external,
run legal_usage_profile_checker and access_grant_checker.
```

PolicyCheckStep should eventually be authored through templates or a constrained
UI. It should not be a general workflow graph.

The authoring model is documented in
`docs/POLICY_CHECK_STEP_AUTHORING_DESIGN.md`. The recommended first
implementation links PolicyCheckSteps to PolicyRules, limits checks to
metadata-only built-ins, and records evidence intent without directly changing
Runtime Gateway decisions.

PolicyCheckStep persistence and CRUD-style API support now exist for this V1
authoring shape. The persistent metadata-only check types are
`access_grant_status`, `data_usage_profile_status`, `source_status`,
`source_classification`, `capability_status`, `model_asset_status`, and
`model_provider_type`. Runtime Gateway can execute active authored steps only
when `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`; execution records
evidence and does not directly change `decision` or `proceed`.

### CheckResult

The safe output of a check.

Suggested fields:

- check_tool;
- check_step_id;
- request_id;
- agent_id;
- source_ids;
- model_id;
- capability_id;
- timestamp;
- outcome;
- confidence;
- safe_reason;
- evidence_reference;
- metadata.

CheckResult must not include raw source content, raw prompts, credentials,
full scanner payloads, or raw tool/model payloads.

The first backend foundation persists CheckResults with safe references,
outcome, optional confidence label, summary, reason, and safe metadata.
Internal helpers can now produce CheckResults for metadata-only AccessGrant,
Data Usage Profile, Source status/classification, Capability, and ModelAsset
status/provider-type checks. They do not execute external scanners or inspect
source contents. Runtime Gateway can optionally execute these helpers behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=false` by default and link resulting
CheckResults to the Agent, run, TraceEvent, and PolicyDecision where available.
CheckResults remain evidence inputs; they do not directly change Runtime
Gateway decisions. They can influence a decision only when an active PolicyRule
explicitly matches safe fields such as `check_type`, `check_outcome`,
`check_target_type`, `check_target_id`, `check_tool_id`, and
`check_min_confidence`.

### CheckRun Or ControlRun

A grouping record for one or more CheckResults produced while evaluating a
runtime request or governance review.

This can be useful when several checks are required before one PolicyDecision.
It should remain a compact evidence grouping, not a workflow execution engine.

### Outcome

Suggested check outcomes:

- `pass`;
- `fail`;
- `unknown`;
- `not_applicable`;
- `unavailable`;
- `requires_review`.

PolicyRules should explicitly decide how outcomes map to `allow`, `deny`, or
`require_human_review`. The implemented deterministic semantics are
any-matching over the CheckResults produced for the current runtime decision:
a rule with `check_*` fields matches when at least one CheckResult satisfies
all specified check conditions.

### Confidence

Confidence is a bounded signal describing check reliability, not a compliance
score or risk score.

Suggested representation:

- `high`;
- `medium`;
- `low`;
- `unknown`.

Numeric confidence may be useful later for scanner adapters, but V1 should use
simple labels to avoid false precision.

### Evidence Reference

A safe pointer to supporting evidence, such as:

- Data Usage Profile ID;
- AccessGrant ID;
- ModelAsset ID;
- external catalog record ID;
- scanner run ID;
- HumanApproval ID;
- DPIA reference.

Evidence references must not include secret URLs, raw payloads, credentials, or
full document contents.

## Example Check Tools

### data_catalog_lookup

Looks up safe catalog metadata for a Source, such as classification tags,
residency labels, owner references, or external catalog IDs.

### pii_detector

Uses a precomputed or external PII signal to determine whether personal data may
be present. V1 should not scan raw source content synchronously.

### dlp_classifier

Reads a DLP classification label or precomputed signal. It should return safe
labels and references, not raw findings.

### secret_scanner

Checks whether a source or sample has a known secret-detection warning. It must
not store detected secret values.

### legal_usage_profile_checker

Evaluates Data Usage Profile fields such as allowed purposes, prohibited
purposes, allowed processing, prohibited processing, review status, review
expiry, DPIA requirement, and DPIA reference.

### access_grant_checker

Checks whether the Agent has active, non-expired AccessGrants for the requested
Source, ModelAsset, Capability, or external target.

### model_provider_risk_checker

Checks ModelAsset provider, model type, status, risk level, and external
provider classification against safe policy context.

### anonymization_checker

Checks whether an approved anonymization or redaction process is declared before
the requested action. V1 should rely on metadata or references, not perform
inline anonymization.

### owner_approval_checker

Checks whether an owner review or HumanApproval exists for the requested use.
This can support escalation and evidence, but should not replace explicit
HumanApproval workflows.

## Decision Flow

Contextual pre-check flow:

```text
Runtime request
-> resolve contextual runtime fields
-> identify applicable PolicyRules
-> optionally run metadata-only PolicyCheckSteps
-> collect CheckResults
-> evaluate decision
-> create PolicyDecision
-> create HumanApproval if needed
-> record Evidence Bundle chain
-> return proceed true or false
```

The first runtime slice runs only metadata-only checks after a TraceEvent and
PolicyDecision are available, so records can be linked without becoming a
hidden enforcement path. Future policy templates may decide which checks are
required before evaluation.

The runtime wrapper or adapter remains responsible for honoring `proceed`.
AGCP records the check evidence, decision, and approval chain; it does not
execute the governed action.

## Runtime Gateway V1 Wiring

Runtime Gateway uses `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED` as the
execution gate:

- when the flag is false, no authored metadata pre-checks run and the existing
  unversioned or active-PolicyVersion evaluation behavior is preserved;
- when the flag is true, Runtime Gateway first finds candidate matched rules
  while ignoring `check_*` conditions, loads active PolicyCheckSteps for those
  rules from the active PolicyVersion snapshot or unversioned fallback rows,
  builds safe `CheckToolRequest` objects, runs the
  `MetadataOnlyCheckToolAdapter`, persists real metadata-derived CheckResults,
  then evaluates PolicyRules again with safe `check_*` context available;
- persistent `source_classification` steps use source selectors and produce
  metadata-only Source/Data Usage Profile classification evidence;
- persistent `model_provider_type` steps use model selectors and produce
  metadata-only ModelAsset provider-type evidence;
- CheckResults are linked to Agent, run, TraceEvent, and final PolicyDecision;
- versioned PolicyCheckStep execution includes safe PolicyVersion metadata when
  the step came from an active PolicyVersion snapshot.

This remains conservative: CheckResults do not automatically enforce
`failure_behavior`; a decision changes only when a PolicyRule explicitly
matches safe `check_type`, `check_outcome`, `check_target_type`,
`check_target_id`, `check_tool_id`, or confidence context. Unsupported selectors
or helper failures create safe error CheckResults instead of fake pass results.

## Check Execution Modes

### Metadata-only Check

Reads AGCP records or safe imported metadata. Examples include AccessGrant
status, Data Usage Profile review status, ModelAsset provider, and Source
classification labels.

This should be the V1 default because it is fast, auditable, and safer for
runtime enforcement.

### External Reference Lookup

May later read a safe external reference from a catalog or scanner system and
return only bounded labels or run IDs. This mode is not implemented in V1 and
must not accept arbitrary URLs, credentials, or raw scanner payloads.

### Sample-based External Scanner

Uses a bounded sample or preapproved external scanner process. This is riskier
because samples may contain sensitive data. Any sample-based design must define
where the sample lives, who can access it, what is stored, and how evidence is
redacted.

### Full Scan

Runs or references a full scan of a Source. This should not happen
synchronously in the runtime request path. Full scans belong in background
governance workflows or external systems, with AGCP storing only safe summaries
and references.

### Async Check

Starts or references an async check and returns `requires_review`, `unknown`, or
another pending-safe outcome. Runtime enforcement should not block indefinitely
on async work.

### Human Review Fallback

If required checks are missing, unavailable, stale, or low confidence, policies
can return `require_human_review`. This keeps uncertainty visible instead of
silently allowing a risky action.

The `human_review_required` execution mode is a representation of this boundary
state, not an instruction for AGCP to approve, reject, or continue a runtime
action by itself.

## Safety And Privacy

Checks must not store, log, audit, or export:

- raw data chunks;
- full source contents;
- full prompts;
- credentials;
- API keys;
- tokens;
- authorization headers;
- private customer data;
- detected secret values;
- full DLP or scanner payloads;
- raw model provider payloads;
- raw tool request or response payloads.

CheckResults should store only:

- safe labels;
- safe summaries;
- outcomes;
- confidence labels;
- safe reasons;
- hashes when needed for correlation;
- evidence references;
- safe metadata after existing filtering rules.

CheckTool adapters must apply metadata safety filtering before persistence,
audit logging, runtime activity, or Evidence Bundle export.

Adapters must also preserve the AGCP boundary: they may prepare governance
facts, but they must not execute the governed tool call, run arbitrary user
code, retrieve raw source documents, or hide `deny`/`require_human_review`
handling from the caller.

## Runtime Implications

Synchronous runtime checks should be limited to fast, deterministic,
metadata-only lookups. Examples:

- active AccessGrant lookup;
- Data Usage Profile purpose check;
- Source review expiry check;
- ModelAsset provider/status check;
- Capability status check.

Checks that require sampling, scanning, external network calls, long-running
jobs, or human judgment should not block runtime enforcement. For those cases,
the decision should usually be `require_human_review`, `deny`, or
`not_applicable` according to explicit policy and failure-mode configuration.

Unavailable check tools must be handled deliberately. Enforcement mode should
prefer fail-closed or require review for high-risk actions, but the default
should be documented per integration before production use.

## Evidence Bundle Implications

Evidence Bundle export includes safe CheckResult summaries when they are linked
to a PolicyDecision in the Agent evidence chain. Agent-scoped CheckResults
without a PolicyDecision link may also appear when they safely belong to the
exported Agent.

Review Inbox read models for Runtime HumanApproval records also surface safe
metadata-only CheckResults when the HumanApproval is linked to a PolicyDecision
that has CheckResults. If no CheckResults are linked, the UI should say
`No metadata pre-check results attached yet.` rather than inventing evidence.

Safe fields may include:

- CheckTool name;
- CheckRun or CheckResult ID;
- timestamp;
- outcome;
- confidence;
- safe reason;
- safe evidence references;
- related Source, Data Usage Profile, ModelAsset, Capability, AccessGrant, and
  HumanApproval IDs.

Evidence Bundle export must not include raw source content, chunks, prompts,
credentials, full scanner results, detected secret values, or raw external
payloads.

CheckResults in Evidence Bundle remain evidence inputs. They do not imply that
pre-checks already drive Runtime Gateway enforcement, replace PolicyDecision,
or certify legal compliance.

## Policy Authoring Implications

Future policy authoring should remain constrained and transparent. A later
Policy Studio could guide users through:

```text
WHEN context matches
RUN checks
THEN decide based on check outcomes
```

Example:

```text
WHEN action_type = vectorize
AND source.data_classification IN confidential, restricted
AND model.provider_type = external
RUN legal_usage_profile_checker
RUN access_grant_checker
THEN deny if either check fails
THEN require_human_review if either check is unknown or unavailable
```

This should be implemented with explicit check types and validated fields, not
arbitrary code, generic workflow graphs, or an unbounded expression language.
Before richer authoring UI expands, Policy, PolicyRule, and PolicyCheckStep
changes should have lightweight versioning, review, activation, and rollback
guardrails so active runtime policy behavior is not changed casually.

Current Policy Studio CHECK blocks compile to deterministic PolicyRule
condition fields, including safe `check_*` outcome summaries. They do not
create CheckTool adapters, run scanners, or author arbitrary check workflows.
PolicyCheckStep UI authoring remains a separate product step after the adapter
boundary, review lifecycle, and runtime semantics are stable.

## Non-goals

- Do not change Runtime Gateway behavior in this foundation.
- Do not change PolicyRule schemas in this foundation.
- Do not add public CRUD APIs in this foundation.
- Do not add scanners in this foundation.
- Do not add external integrations in this foundation.
- Do not add webhooks or arbitrary callback endpoints in this foundation.
- Do not add frontend UI in this foundation.
- Do not execute arbitrary tools.
- Do not send raw source contents to external tools.
- Do not turn AGCP into an orchestrator or workflow engine.
- Do not run expensive scans synchronously in runtime enforcement.
- Do not replace DLP systems, data catalogs, DPOs, legal counsel, or governance
  review processes.
- Do not claim legal compliance certification or automatic lawful-use
  determination.
- Do not add fake compliance scores, maturity scores, trust scores, or
  numerical risk scores.

## Migration Path

Recommended staged implementation:

1. Finalize this design and align it with contextual runtime governance and
   Data Usage Profile. Implemented.
2. Add a CheckTool registry model for known internal metadata-only checks.
   Implemented as backend persistence only.
3. Add CheckResult persistence with safe metadata filtering.
   Implemented as backend persistence and an internal helper.
4. Support metadata-only checks first for Data Usage Profile, AccessGrant,
   ModelAsset, Capability, and Source status. Implemented as internal helpers.
4a. Define a formal CheckTool adapter boundary with safe request/result
    objects and metadata-only adapter checks for AccessGrant status,
    Data Usage Profile status, Source status/classification, ModelAsset
    status/provider type, and Capability status. Implemented.
4b. Wire Runtime Gateway metadata pre-check execution through the
    metadata-only adapter boundary behind
    `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`, while preserving disabled
    flag behavior and requiring explicit `check_*` PolicyRule matching for
    decision changes. Implemented.
5. Connect CheckResults to PolicyDecision and Evidence Bundle export.
   Evidence Bundle export implemented for safe CheckResult summaries.
6. Design explicit PolicyCheckStep support for a small set of PolicyRule or
   policy template use cases. Done in
   `docs/POLICY_CHECK_STEP_AUTHORING_DESIGN.md`.
7. Add PolicyCheckStep persistence and API support for metadata-only checks.
   Implemented as PolicyRule-linked authoring/configuration only.
8. Wire Runtime Gateway metadata-only pre-check execution to authored active
   PolicyCheckSteps behind `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`.
   Implemented as evidence-only execution.
9. Add deterministic CheckResult outcome matching for PolicyRules. Implemented
   with explicit `check_*` condition fields and no automatic
   `failure_behavior` enforcement.
10. Add persistent PolicyCheckStep check types for `source_classification` and
   `model_provider_type`, wired to the metadata-only adapter. Implemented.
11. Add async check handling and HumanApproval fallback behavior.
12. Later add external checker adapters for catalogs, DLP, PII scanners, and
   secret scanners after safety boundaries are clear.
13. Implement lightweight policy versioning and review guardrails before
    expanding PolicyCheckStep or check-based authoring UI.
14. Later add a constrained Policy Studio UI for check-based policy authoring.

Pre-checks should stay optional until runtime context and Data Usage Profile
are implemented. They should not become required infrastructure for the current
Runtime Gateway contract.

## Open Questions

- Should PolicyCheckSteps attach only to PolicyRule in V1, or should
  Policy-level defaults be supported immediately?
- Should failed checks deny by default or require human review by default?
- How should confidence thresholds be represented without creating fake scores?
- How should unavailable check tools behave in simulation versus enforcement
  mode?
- How can AGCP avoid latency in runtime enforcement while still providing useful
  control evidence?
- Which metadata-only checks are safe enough for the first implementation?
- Should CheckResults be immutable evidence records with replacement-by-new-run
  semantics?
- How long should CheckResults remain reusable before they become stale?
- How should external scanner references be validated without importing unsafe
  scanner payloads?
- Should the existing runtime metadata pre-check helpers be gradually adapted
  to call the formal `CheckToolAdapter` contract, or should the contract remain
  a boundary for future external adapters only?
