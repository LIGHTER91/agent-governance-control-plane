# Contextual Runtime Governance Design

## Status

Partially implemented design. The original contextual runtime governance design
has been implemented in several bounded slices, while the broader production
governance model remains intentionally staged.

Implemented slices:

- optional Runtime Gateway context fields for action, capability, source,
  model, purpose, data classification, and personal/sensitive-data booleans;
- safe persistence of declared contextual references and metadata;
- metadata-only Policy Pre-Check persistence and opt-in Runtime Gateway
  execution behind `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true`;
- deterministic PolicyRule matching for a bounded set of declared and
  inventory-resolved contextual fields;
- Evidence Bundle summaries for available contextual references, CheckResults,
  PolicyVersion references, and HumanApproval chains;
- Policy Studio support for CHECK facts and explicit PolicyCheckStep authoring
  in the Blocks workflow.

Still design or future work:

- production identity, RBAC, and service actor hardening;
- AccessGrant-aware enforcement semantics beyond resolved context;
- richer PolicyCheckStep templates and backend authoring workflows;
- historical PolicyDecision backfill semantics;
- signed or PDF evidence exports;
- browser E2E coverage for all contextual governance workflows.

AGCP remains a governance and evidence control plane. It does not execute
tools, orchestrate agent steps, replace agent runtimes, or certify that data use
is legally compliant.

## Critical Assessment

Contextual runtime governance is strategically important because real agentic
actions are rarely governed safely by `tool_name`, `environment`, and Agent
`risk_level` alone. A request to vectorize public product documentation with an
approved local embedding model is very different from a request to vectorize
confidential HR data with an external embedding model API, even if both appear
as the same generic tool call.

Richer context helps AGCP answer higher-value governance questions:

- Which Agent is requesting the action?
- What action is being requested?
- Which Capability, Source, and ModelAsset records are involved?
- What classification or sensitivity applies to the data?
- Which provider or external system would receive the data?
- What purpose was declared for the action?
- Is there an active AccessGrant for the Agent and target?
- Which PolicyRule allowed, denied, or escalated the action?
- Is HumanApproval required before the wrapper or adapter proceeds?
- What safe evidence can later explain the decision?

This direction is useful for RAG, vectorization, model routing, external API
calls, data access, and other governed actions. It also carries risks. If AGCP
collects too much runtime detail, it could become a store of sensitive prompts,
document chunks, customer records, credentials, or provider payloads. If it
tries to execute or route those actions, it drifts into orchestration. If it
accepts arbitrary policy expressions over large runtime payloads, it drifts into
a generic policy engine and may weaken the deterministic evaluator. The design
therefore favors stable identifiers, classifications, booleans, and safe
metadata over raw content.

## Problem Statement

The current Runtime Gateway foundation can record and evaluate requests around
Agent identity, run identity, request identity, `tool_name`, `environment`,
Agent `risk_level`, runtime mode, and safe metadata. That is enough for a V0/V1
tool-call governance contract, but not enough for contextual decisions such as:

```text
Agent RAG wants to vectorize confidential source data using an external
embedding model API.
```

To govern this honestly, AGCP eventually needs to reason over:

```text
Agent
+ Action
+ Source
+ Data classification
+ Model
+ Provider
+ Capability
+ Purpose
+ Environment
+ AccessGrant
+ Approval state
```

The Runtime Gateway should remain the decision and evidence layer for this
context. It should not become the component that retrieves documents, embeds
data, calls model providers, schedules workflows, or executes tools.

## Example Use Cases

### RAG Source Vectorization With External Embedding Model

An Agent asks to vectorize a knowledge source. The request includes a source
reference, an embedding model reference, a capability reference, and a declared
purpose such as `semantic_search_indexing`.

Future contextual policies could require HumanApproval or deny the request when
the source is confidential and the model provider is external unless an active
AccessGrant exists for both the source and model.

### Confidential Source Used In Production

An Agent in `production` requests retrieval from a restricted source. The
request references the Source record and carries safe data classification
fields. A policy can distinguish production use of restricted data from
development use of low-risk internal documentation.

### Missing AccessGrant For Source, Model, Or Capability

An Agent requests a governed action against a Source, ModelAsset, or Capability
that is not covered by an active AccessGrant. The gateway can later deny,
escalate, or mark the request as not applicable depending on policy.

### Unapproved Model Provider

An Agent requests to send data to a model provider that is not approved for the
Agent, environment, data classification, or purpose. The model inventory record
can provide provider and model metadata without storing credentials or raw
provider payloads.

### Unknown Or Incompatible Purpose

An Agent requests access with no declared purpose, or with a purpose that does
not match the grant or policy. For example, a grant may allow
`customer_support_answering` but not `training_data_generation`.

## Proposed Runtime Context Fields

These fields are the contextual extension to the runtime request context. The
first implementation slice introduces the core fields as optional values so
existing Runtime Gateway clients continue to work.

| Field | Purpose | Notes |
| --- | --- | --- |
| `agent_id` | Agent requesting the action | Already required today. |
| `run_id` | Agent run grouping the action | Already required today. |
| `request_id` | Idempotency key for the request | Already required today. |
| `action_type` | Governed action category | Examples: `vectorize`, `retrieve`, `generate`, `summarize`, `send_email`, `write_db`, `call_api`. |
| `capability_id` | Inventory Capability reference | Preferred when the caller can reference an AGCP Capability. |
| `capability_ref` | External capability reference | Useful before a Capability record exists. |
| `tool_name` | Backward-compatible tool name | Existing clients can continue to send this. |
| `source_ids` | Source inventory references | Multiple sources may be involved in RAG or summarization. |
| `model_id` | ModelAsset inventory reference | Useful for LLM, embedding, reranker, classifier, or other model use. |
| `purpose` | Declared purpose of the action | Examples: `semantic_search_indexing`, `customer_support_answering`, `incident_triage`. |
| `environment` | Runtime environment | Should keep using the existing Environment vocabulary. |
| `risk_level` | Caller or Agent risk context | Should keep using the existing Risk Level vocabulary. |
| `data_classification` | Data sensitivity classification | May be caller-supplied, resolved from Data Usage Profile, or both; behavior must be explicit before enforcement. |
| `contains_personal_data` | Safe boolean signal | Does not include the data itself. |
| `contains_sensitive_data` | Safe boolean signal | Does not include the data itself. |
| `metadata` | Additional safe context | Must use the existing safe metadata filtering rules. |

The request must not include raw source content, retrieved chunks, prompts that
may contain secrets or private data, credentials, API keys, authorization
headers, full documents, raw model payloads, or raw tool payloads.

## Backward Compatibility

The current runtime tool-call contract should remain valid. Existing clients
that send `request_id`, `agent_id`, `run_id`, `tool_name`, `action_summary`,
`mode`, and safe `metadata` should continue to receive the same decision
contract.

The contextual fields should be optional during the first implementation slice.
When they are absent, AGCP should not invent missing values. Runtime activity,
Evidence Bundle records, and policy context should represent unknown fields as
`null`, empty lists, or omitted fields according to the API schema.

`tool_name` can continue to act as the backward-compatible capability signal.
`capability_id` should be preferred once clients can reference inventory
records. `capability_ref` can bridge external system names before the
Capability inventory is fully populated.

## Inventory Resolution

Later runtime processing can resolve contextual references before policy
evaluation:

- `source_ids` -> Source inventory records;
- Source inventory records -> Data Usage Profile records when available;
- `model_id` -> ModelAsset inventory record;
- `capability_id` -> Capability inventory record;
- `(agent_id, target_type, target_id)` -> active AccessGrant records;
- contextual fields -> deterministic PolicyRule matching context.

Resolution should produce a compact internal decision context. That context can
include safe inventory fields such as IDs, type, status, provider, risk level,
classification, usage purpose constraints, review status, and ownership
references. It must not include source contents, credentials, raw prompts, or
raw payloads.

The Source side of contextual governance needs the Data Usage Profile design in
`docs/DATA_USAGE_PROFILE_DESIGN.md`. Source inventory identifies the data
source; Data Usage Profile describes safe governance metadata such as
classification, personal or sensitive data signals, allowed and prohibited
purposes, allowed and prohibited processing, review status, DPIA references, and
review expiry. These fields are decision support and evidence context, not legal
certification.

Unknown inventory references require an explicit future policy. Conservative
options include fail-closed in enforcement mode, require human review in
simulation, or return a validation error before creating a misleading
PolicyDecision. The initial implementation should document the chosen behavior
before enabling contextual enforcement.

## Decision Flow

The future contextual decision flow should be:

```text
Runtime request
-> validate request and safe metadata
-> resolve inventory context
-> run required metadata-only policy pre-checks when configured
-> check AccessGrants for Agent and targets
-> evaluate contextual policies
-> create PolicyDecision
-> create HumanApproval if needed
-> record evidence chain
-> return proceed true or false
```

The wrapper or adapter remains responsible for honoring `proceed`. AGCP records
the governance decision and evidence chain; it does not execute the action.

AccessGrant checks should inform policy evaluation and evidence, but they
should not replace PolicyDecision records. A missing or expired grant is a
governance fact that a PolicyRule can use to allow, deny, or require review.

Policy Pre-Checks are a related future design in
`docs/POLICY_PRE_CHECKS_DESIGN.md`. They should provide safe CheckResults for
facts such as Data Usage Profile review status, AccessGrant status, ModelAsset
provider approval, Source classification, or DLP labels. Pre-checks should start
as metadata-only lookups and should not execute arbitrary tools or long-running
scans in the runtime path.

## PolicyRule Connection

The current PolicyRule condition format is intentionally small and
deterministic. Contextual governance extends that approach through explicit
field matching instead of a broad expression language.

Implemented contextual rule matching supports declared Runtime Gateway fields
and safe inventory-resolved fields.

Declared fields:

- `action_type`;
- `capability_id`;
- `source_id` or `source_ids`;
- `model_id`;
- `purpose`;
- `data_classification`;
- `contains_personal_data`;
- `contains_sensitive_data`.

Inventory-resolved fields:

- `declared_data_classification`;
- `capability_type`;
- `capability_status`;
- `source_status` or `source_statuses`;
- `source_data_classification` or `source_data_classifications`;
- `source_contains_personal_data`;
- `source_contains_sensitive_data`;
- `model_type`;
- `model_provider`;
- `model_provider_type`;
- `model_status`;
- `access_grant_status` or `access_grant_statuses`;
- `data_usage_review_status` or `data_usage_review_statuses`;
- `data_usage_allowed_purpose` or `data_usage_allowed_purposes`;
- `data_usage_prohibited_purpose` or `data_usage_prohibited_purposes`.

Matching remains deterministic. Missing or `null` optional condition fields are
wildcards, and `source_ids` matches when any declared source ID overlaps the
Runtime Gateway request `source_ids`. List-valued resolved fields match when
any rule value overlaps the resolved context. Missing inventory references are
represented as `missing`, not silently treated as safe.

Future contextual rule matching may add additional inventory-resolved fields
such as:

- `source_allowed_purposes`;
- `source_prohibited_purposes`;
- `source_allowed_processing`;
- `source_prohibited_processing`;
- model risk/provider approval categories;
- AccessGrant owner or review references when safe.

Unsupported fields should continue to be rejected rather than interpreted
implicitly. Caller-supplied classifications and personal/sensitive-data flags
are declared context only; they are not verified Source/Data Usage Profile
truth. AccessGrant status is resolved as context only and is not automatically
enforced until explicit AccessGrant-aware policy behavior is added.

## Evidence Bundle And Activity Connection

Contextual runtime decisions should eventually appear in Runtime activity,
Agent activity, Agent Governance Profile summaries, and Evidence Bundle export.

Evidence should remain compact and safe:

- include referenced IDs and safe inventory references;
- include the PolicyDecision and HumanApproval chain;
- include AccessGrant references used by the decision when safely available;
- include Data Usage Profile summary fields such as data classification, review
  status, and purpose constraints when safe;
- include data classification and purpose when safe;
- exclude raw content and raw provider/tool payloads.

Evidence Bundle export should not become a full data catalog or a UI profile.
It should provide enough safe evidence to answer why a contextual runtime
decision happened.

## Metadata Safety

AGCP must not store, log, audit, or export:

- raw source content;
- retrieved chunks;
- full documents;
- prompts that may contain sensitive data;
- private customer data;
- API keys;
- tokens;
- credentials;
- authorization headers;
- full model provider payloads;
- full tool request or response payloads;
- unsafe metadata values that fail existing metadata safety rules.

Runtime clients should send references, classifications, booleans, short
summaries, and purpose strings. If a caller cannot safely summarize a request,
the integration should omit the field or use a stable reference that can be
reviewed in the source system.

## Non-goals

- Do not expand Runtime Gateway schemas outside the bounded contextual fields
  already documented in this design.
- Do not add arbitrary policy expression languages or LLM-based policy
  evaluation.
- Do not treat AccessGrant status as automatic runtime enforcement until
  explicit PolicyDecision semantics are designed and tested.
- Do not change Runtime Gateway enforcement behavior without preserving the
  wrapper/adapter responsibility to honor `proceed`.
- Do not execute tools or route agent workflows.
- Do not replace LangGraph, n8n, Dataiku, CrewAI, AutoGen, cloud AI platforms,
  MCP servers, model providers, DLP systems, data catalogs, or orchestration
  runtimes.
- Do not legally certify data usage or claim compliance certification.
- Do not replace a DPO, legal counsel, DLP process, or data governance program.
- Do not add fake compliance scores, maturity scores, or trust scores.

## Migration Path

Recommended staged implementation:

1. Design the contextual runtime schema and document accepted values. Done.
2. Add Data Usage Profile persistence for Source governance context. Done.
3. Add Policy Pre-Checks for metadata-only control checks that can produce safe
   CheckResults. Initial persistence, helpers, Evidence Bundle summaries, and
   opt-in Runtime Gateway execution behind
   `AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true` are done.
   PolicyCheckStep authoring is designed for explicit PolicyRule-linked check
   requirements.
4. Add optional contextual fields to the runtime request schema. Done for
   `action_type`, `capability_id`, `source_ids`, `model_id`, `purpose`,
   `data_classification`, `contains_personal_data`, and
   `contains_sensitive_data`.
5. Persist only safe context metadata and references on runtime records. Done
   for the optional request fields, without inventory resolution.
6. Update Runtime activity and Evidence Bundle export with safe contextual
   references. Done where values are present on TraceEvent metadata.
7. Extend the deterministic policy evaluator with a small, explicit set of
   contextual fields. Done for declared and safe resolved context fields.
8. Add policy templates for common governance cases such as external
   vectorization, restricted-source retrieval, and unapproved model provider
   usage.
9. Later add a Policy Studio or guided UI for contextual policies only after
   versioning, review, and simulation semantics are designed.

Each stage should keep existing clients working and should avoid treating
AccessGrants as runtime enforcement until PolicyDecision semantics explicitly
use them.

## Open Questions

- Should `data_classification` be sent by the caller, resolved from Source Data
  Usage Profile, or both?
- How should multiple sources with different classifications be represented?
- Should `purpose` be required for production enforcement requests?
- How should future confidence or uncertainty from checks be represented
  without creating fake scores?
- How should unknown Source, ModelAsset, or Capability references be handled in
  simulation versus enforcement mode?
- Which contextual fields should become PolicyRule match fields first?
- Should AccessGrant expiration and status be precomputed into runtime context
  or evaluated directly during policy matching?
- How should AGCP avoid leaking sensitive source identifiers when source names
  or external refs are themselves sensitive?
