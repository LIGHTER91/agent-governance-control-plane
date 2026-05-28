# Domain Model

This document defines the core product vocabulary.

Codex must use these names consistently.

## Agent

An AI-powered system that can reason, call models, use tools, access data, and/or perform actions.

Suggested fields:

- id;
- name;
- description;
- owner_type;
- owner_id;
- owner_name;
- owner_contact_email;
- environment;
- status;
- risk_level;
- framework;
- created_at;
- updated_at.

## Agent Owner

The accountable owner for an agent.

Owners may be represented before full identity integration exists. Email may be stored as a nullable contact field, but it is not the primary owner identifier.

Allowed owner types initially:

- user;
- team;
- service;
- organization_unit.

Suggested fields:

- owner_type;
- owner_id;
- owner_name;
- owner_contact_email.

Owner identity convention:

- `owner_type = "user"` -> `owner_id = "user:<external-id>"`;
- `owner_type = "team"` -> `owner_id = "team:<slug>"`;
- `owner_type = "service"` -> `owner_id = "service:<slug>"`;
- `owner_type = "organization_unit"` -> `owner_id = "org_unit:<slug>"`.

## Environment

Where the agent operates.

Allowed values initially:

- development;
- staging;
- production.

## Agent Status

Lifecycle status.

Allowed values initially:

- draft;
- under_review;
- approved;
- active;
- suspended;
- retired.

## Risk Level

Initial risk classification.

Allowed values initially:

- low;
- medium;
- high;
- critical.

Do not create numerical risk scores yet.

## Capability

An inventory record describing a governed operation an Agent may use, such as a
tool, API, integration, workflow action, or other capability.

Suggested fields:

- id;
- name;
- description;
- capability_type;
- external_ref;
- status;
- risk_level;
- metadata;
- created_at;
- updated_at.

Allowed capability types initially:

- tool;
- api;
- integration;
- workflow_action;
- other.

Allowed capability statuses initially:

- active;
- disabled;
- retired.

Capability metadata must contain only safe, non-sensitive context. Do not store
raw prompts, credentials, tokens, secrets, authorization headers, or raw
sensitive payloads in capability metadata.

Capabilities can be referenced by Access Grants, surfaced through the Agent
Governance Profile read model and UI, and included as safe Evidence Bundle
references when granted to an Agent. Runtime enforcement and broader workflow
review for these declared grants remain future work.

## Tool

An external capability the agent can call.

Examples:

- send_email;
- query_database;
- create_ticket;
- web_search;
- call_internal_api;
- update_crm.

## Data Source

A governed inventory record describing a source of information an Agent may
access, such as a knowledge base, database, document store, API, bucket,
filesystem, or other data or knowledge source.

Suggested fields:

- id;
- name;
- description;
- source_type;
- external_ref;
- owner_type;
- owner_id;
- owner_name;
- owner_contact_email;
- status;
- risk_level;
- metadata;
- created_at;
- updated_at.

Allowed source types initially:

- knowledge_base;
- database;
- document_store;
- api;
- bucket;
- filesystem;
- other.

Allowed source statuses initially:

- active;
- disabled;
- retired.

Examples:

- internal_docs;
- customer_records;
- HR_data;
- support_tickets;
- vector_database;
- SharePoint;
- Dataiku dataset.

Source metadata must contain only safe, non-sensitive context. Do not store raw
source contents, credentials, tokens, secrets, authorization headers, raw
prompts, private customer data, or raw sensitive payloads in Source inventory
metadata.

Sources can be referenced by Access Grants, surfaced through the Agent
Governance Profile read model and UI, and included as safe Evidence Bundle
references when granted to an Agent. Runtime enforcement and permission
semantics for source access remain future work.

## Data Usage Profile

A governance profile linked to a Source that describes safe, declared usage
context for contextual runtime governance.

The design is documented in `docs/DATA_USAGE_PROFILE_DESIGN.md`. The first
backend foundation is implemented as a separate object linked one-to-one with
Source, exposed through `/sources/{source_id}/usage-profile`. Runtime Gateway
context, policy evaluation, and Policy Pre-Checks do not use it yet. Evidence
Bundle export includes safe Data Usage Profile summaries for Sources referenced
by an Agent's Access Grants.

Data Usage Profile holds classification, purpose constraints, processing
constraints, review status, DPIA references, and safe metadata that can evolve
on a different cadence than Source identity and lifecycle.

Implemented fields:

- source_id;
- data_classification;
- contains_personal_data;
- contains_sensitive_data;
- data_categories;
- legal_basis;
- allowed_purposes;
- prohibited_purposes;
- allowed_processing;
- prohibited_processing;
- residency;
- retention_policy;
- data_owner;
- review_status;
- dpia_required;
- dpia_reference;
- reviewed_by_actor_type;
- reviewed_by_actor_id;
- reviewed_at;
- review_expires_at;
- metadata.

Data Usage Profile metadata must contain only safe, non-sensitive context. It
must not include raw source content, retrieved chunks, full documents, prompts,
credentials, tokens, secrets, private customer data, or raw scanner payloads.

Scanner, catalog, DLP, and caller-provided signals can support review workflows,
but they are not legal truth. AGCP should use Data Usage Profile as decision
support, policy context, and evidence, not as legal compliance certification or
automatic lawful-use determination.

Mutations append `data_usage_profile_created`,
`data_usage_profile_updated`, or
`data_usage_profile_review_status_changed` audit records with safe metadata
summaries.

## Model

A governed inventory record describing an AI/ML model or model endpoint an
Agent may use, such as a hosted LLM, embedding model, reranker, classifier,
vision model, audio model, local model, or other model asset.

The backend implementation uses `ModelAsset` as the Python domain class name to
avoid collisions with SQLAlchemy terminology.

Suggested fields:

- id;
- name;
- description;
- model_type;
- provider;
- model_ref;
- version;
- owner_type;
- owner_id;
- owner_name;
- owner_contact_email;
- status;
- risk_level;
- metadata;
- created_at;
- updated_at.

Allowed model types initially:

- llm;
- embedding;
- reranker;
- classifier;
- vision;
- audio;
- other.

Allowed providers initially:

- openai;
- mistral;
- anthropic;
- local;
- azure;
- aws;
- gcp;
- other.

Allowed model statuses initially:

- active;
- disabled;
- retired.

Model metadata must contain only safe, non-sensitive context. Do not store
credentials, tokens, secrets, authorization headers, raw prompts, private
customer data, or raw sensitive payloads in Model inventory metadata.

Model inventory records do not call model provider APIs and do not store
credentials. Models can be referenced by Access Grants, surfaced through the
Agent Governance Profile read model and UI, and included as safe Evidence
Bundle references when granted to an Agent. Runtime enforcement and permission
semantics for model access remain future work.

## Access Grant

A governed inventory record declaring that an Agent is allowed to use a
Capability, Source, ModelAsset, external target, or other governed target.

Access Grants help answer:

- what an Agent is allowed to use;
- who granted that access;
- when the grant was recorded;
- whether the grant is pending review, active, suspended, revoked, or expired;
- what safe evidence or context supports the grant.

Suggested fields:

- id;
- name;
- description;
- grant_type;
- subject_type;
- subject_id;
- target_type;
- target_id;
- external_ref;
- status;
- granted_by_actor_type;
- granted_by_actor_id;
- reason;
- expires_at;
- risk_level;
- metadata;
- created_at;
- updated_at.

Allowed grant types initially:

- capability;
- source;
- model;
- permission;
- other.

Allowed subject types initially:

- agent.

Allowed target types initially:

- capability;
- source;
- model_asset;
- external;
- other.

Allowed statuses initially:

- pending_review;
- active;
- suspended;
- revoked;
- expired.

The API sets `granted_by_actor_type` and `granted_by_actor_id` from the current
ActorContext when the grant is created. Callers should not supply or override
grantor fields.

Access Grants are declarations, not enforcement decisions. They must not become
a full IAM system, and they must not replace PolicyDecision, Runtime Gateway, or
HumanApproval records. For now, Access Grants are the association layer between
Agents and governed inventory targets. Separate AgentCapability, AgentSource, or
AgentModel join tables should not be added unless AccessGrant semantics prove
insufficient for a concrete governance question.

`GET /agents/{agent_id}/access-grants` reads an Agent's declared grants newest
first, with minimal filters for `status` and `target_type`. The Agent
Governance Profile UI surfaces these grants as compact inventory and access
details. Evidence Bundle export includes Agent-scoped Access Grants and safe
Capability, Source, and ModelAsset references for granted inventory targets.
Later work may use grants as policy context.

Access Grant metadata must contain only safe, non-sensitive context. Do not
store credentials, tokens, secrets, authorization headers, raw prompts, private
customer data, or raw sensitive payloads in Access Grant metadata.

## Runtime Governance Context

A future runtime decision context that combines safe references and
classifications needed for contextual governance decisions.

The design is documented in
`docs/CONTEXTUAL_RUNTIME_GOVERNANCE_DESIGN.md`. It is design-only for now; no
runtime schema, persistence model, or evaluator behavior has changed yet.

Suggested future fields:

- agent_id;
- run_id;
- request_id;
- action_type;
- capability_id;
- capability_ref or tool_name for backward compatibility;
- source_ids;
- model_id;
- purpose;
- environment;
- risk_level;
- data_classification;
- contains_personal_data;
- contains_sensitive_data;
- metadata.

Runtime Governance Context should use references, classifications, booleans,
and short safe summaries. It must not include raw source content, retrieved
chunks, full documents, prompts that may contain sensitive data, API keys,
credentials, authorization headers, full model provider payloads, or raw tool
payloads.

Later work may resolve contextual references to Source, Data Usage Profile,
ModelAsset, Capability, and AccessGrant records before deterministic PolicyRule
evaluation. This should extend PolicyDecision evidence rather than replace
PolicyDecision, HumanApproval, AuditLog, or Evidence Bundle records.

## Agent Governance Profile

A compact read model for one Agent's current governance posture.

`GET /agents/{agent_id}/governance-profile` returns Agent metadata, owner,
environment, status, risk level, recent governance activity, recent
HumanApproval summary, Agent-scoped Access Grants, safe references to granted
Capability, Source, and ModelAsset targets, policy/rule ID references derived
from PolicyDecision records, and an Evidence Bundle export hint.

The profile supports product navigation and the frontend Agent Governance
Profile UI. It is not an Evidence Bundle export, does not include full audit
logs, run history, trace event history, or full policy decision history, and
must not be treated as a compliance certification. Evidence Bundle JSON export
remains the canonical audit/review export.

The profile should stay bounded and read-optimized. Broad filtering,
pagination, full history joins, policy simulation, policy evaluation changes,
charts, compliance scores, and frontend-specific presentation state remain out
of scope for this backend read model.

## Policy

A governance rule or set of rules applied to agents.

Suggested fields:

- id;
- name;
- description;
- status;
- created_at;
- updated_at.

Allowed statuses initially:

- draft;
- active;
- disabled;
- archived.

`POST /policies`, `GET /policies`, `GET /policies/{policy_id}`, and
`PATCH /policies/{policy_id}` manage Policy lifecycle records. The API uses the
status lifecycle instead of hard delete. Mutations append `policy_created`,
`policy_updated`, or `policy_status_changed` audit records.

Policy management and PolicyRule management are separate API surfaces. Policy
lifecycle changes happen through `/policies`; rule condition changes happen
through `/policy-rules`.

Examples:

- "Production agents must have an owner."
- "High-risk agents require human approval before external actions."
- "HR agents cannot access raw protected attributes."
- "Only approved agents can call send_email."

## Policy Rule

A single rule within a policy.

Initial rule format should be simple and explicit.

Avoid building a full DSL too early.

Supported persisted `condition` shape for the first evaluator adapter:

```json
{
  "decision": "allow",
  "reason": "The requested action is allowed for this context.",
  "agent_id": "optional-agent-id",
  "tool_name": "optional_tool_name",
  "environment": "development",
  "risk_level": "low",
  "action_type": "vectorize",
  "capability_id": "12121212-1212-4121-8121-121212121212",
  "source_ids": ["13131313-1313-4131-8131-131313131313"],
  "model_id": "14141414-1414-4141-8141-141414141414",
  "purpose": "semantic_search_indexing",
  "data_classification": "confidential",
  "declared_data_classification": "confidential",
  "source_data_classification": "restricted",
  "model_provider_type": "external",
  "access_grant_status": "active",
  "data_usage_review_status": "approved",
  "contains_personal_data": true,
  "contains_sensitive_data": false
}
```

Required fields:

- `decision`: one of `allow`, `deny`, `require_human_review`, or `not_applicable`;
- `reason`: non-empty human-readable explanation.

Optional matching fields:

- `agent_id`;
- `tool_name`;
- `environment`: one of `development`, `staging`, or `production`;
- `risk_level`: one of `low`, `medium`, `high`, or `critical`;
- `action_type`;
- `capability_id`;
- `source_id` or `source_ids`;
- `model_id`;
- `purpose`;
- `data_classification`: one of `public`, `internal`, `confidential`, or
  `restricted`;
- `declared_data_classification`: caller-declared data classification, kept
  distinct from resolved Source profile classification;
- `contains_personal_data`;
- `contains_sensitive_data`;
- `capability_type`;
- `capability_status`: capability status or `missing`;
- `source_status` or `source_statuses`: Source status values or `missing`;
- `source_data_classification` or `source_data_classifications`;
- `source_contains_personal_data`;
- `source_contains_sensitive_data`;
- `model_type`;
- `model_provider`;
- `model_provider_type`: `local`, `external`, or `unknown`;
- `model_status`: model status or `missing`;
- `access_grant_status` or `access_grant_statuses`: AccessGrant status values
  or `missing`;
- `data_usage_review_status` or `data_usage_review_statuses`: review status
  values or `missing`;
- `data_usage_allowed_purpose` or `data_usage_allowed_purposes`;
- `data_usage_prohibited_purpose` or `data_usage_prohibited_purposes`.

Contextual matching is still deterministic field matching, not a DSL. Missing
or `null` optional fields are wildcards. A `source_id` condition matches any
source ID in the Runtime Gateway request, and a `source_ids` condition matches
when any declared source ID overlaps the request `source_ids`. List-valued
resolved fields use the same any-overlap matching. Caller-supplied
classification and personal/sensitive-data flags are declared context only, not
verified Data Usage Profile truth. Resolved AccessGrant statuses are policy
context only and are not automatically enforced by the Runtime Gateway.

Unsupported condition fields must be rejected rather than interpreted implicitly.

Suggested fields:

- id;
- policy_id;
- name;
- description;
- condition;
- created_at;
- updated_at.

`POST /policy-rules`, `GET /policy-rules`, `GET /policy-rules/{rule_id}`, and
`PATCH /policy-rules/{rule_id}` manage PolicyRule records. `GET
/policies/{policy_id}/rules` reads rules scoped to one Policy. The API does not
support hard delete.

PolicyRule conditions are still stored as strings in the existing model, but API
writes validate that the string is a JSON object using the deterministic shape
above. This keeps rule management aligned with the existing evaluator without
turning AGCP into a generic policy-language platform.

PolicyRule mutations append `policy_rule_created` or `policy_rule_updated`.
Audit metadata must not include full rule conditions; conditions can contain
operational details such as tool names and reasons.

## Policy Pre-Check

A governed control check that can produce safe, auditable inputs for a future
PolicyDecision.

The design is documented in `docs/POLICY_PRE_CHECKS_DESIGN.md`. It is
implemented as a first backend persistence and internal helper foundation for
metadata-only checks. Runtime Gateway behavior, PolicyRule schemas, scanner
integration, public CRUD APIs, frontend UI, and external integrations have not
changed yet.

Implemented concepts:

- CheckTool;
- CheckResult;

Future concepts:

- PolicyCheckStep;
- CheckRun or ControlRun;
- outcome;
- confidence;
- evidence_reference.

Policy Pre-Checks should differ from policy evaluation itself. A check gathers
or verifies a bounded fact, such as AccessGrant status, Data Usage Profile
review state, Source classification, ModelAsset provider status, or safe DLP
classification. Policy evaluation uses those facts to produce a deterministic
decision.

Policy Pre-Checks must not become workflow orchestration or arbitrary tool
execution. V1 should start with metadata-only checks over AGCP records and safe
imported metadata. Expensive scans, external network calls, and human judgment
should be async, precomputed, or routed to HumanApproval rather than blocking
the runtime path.

CheckResult metadata must contain only safe, non-sensitive context. It must not
include raw source content, retrieved chunks, full prompts, credentials, tokens,
detected secret values, full scanner payloads, private customer data, or raw
tool/model provider payloads.

CheckTool records describe known metadata-only check capabilities such as
AccessGrant, Data Usage Profile, Source status, ModelAsset status, and
Capability status checks. CheckResult records can reference an Agent, run,
TraceEvent, PolicyDecision, and a checked target by safe IDs. They store only
outcome, optional confidence label, safe summary, safe reason, and safe
metadata. Internal helpers can generate CheckResults for AccessGrant status,
Data Usage Profile review status, and Source, Capability, and ModelAsset
inventory status. Evidence Bundle export includes safe CheckResult summaries
linked to the Agent through PolicyDecisions or Agent-scoped pre-check records.
Runtime Gateway can optionally run these metadata-only helpers behind
`AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=true` and link CheckResults to the
Agent, run, TraceEvent, and PolicyDecision where available. CheckResults are
evidence inputs; they do not replace PolicyDecision and do not directly change
Runtime Gateway decisions.

## Policy Decision

A recorded result of evaluating a policy.

Allowed decisions initially:

- allow;
- deny;
- require_human_review;
- not_applicable.

Suggested fields:

- id;
- agent_id;
- policy_id;
- rule_id;
- decision;
- reason;
- context_hash;
- created_at.

## Agent Run

A single execution of an agent.

Suggested fields:

- id;
- agent_id;
- run_id;
- correlation_id;
- environment;
- started_at;
- ended_at;
- status;
- summary;
- metadata.

## Trace Event

An event emitted during an agent run.

Suggested fields:

- id;
- agent_id;
- run_id;
- correlation_id;
- event_type;
- timestamp;
- summary;
- metadata.

Examples:

- model_call_started;
- model_call_completed;
- tool_call_requested;
- tool_call_allowed;
- tool_call_denied;
- human_review_requested;
- error;

Runtime TraceEvent metadata may include optional contextual references and
labels such as action type, Capability ID, Source IDs, ModelAsset ID, purpose,
declared data classification, and personal or sensitive data booleans. These
values are evidence context only until explicit contextual policy evaluation is
implemented. Trace event metadata must contain only safe, non-sensitive context.
Do not store raw source content, chunks, prompts, credentials, tokens, secrets,
authorization headers, scanner payloads, or raw sensitive payloads in telemetry
metadata.

## Actor

The source responsible for a governance-relevant action.

Initial actor types:

- system;
- user;
- service;
- development.

Before full authentication exists, audit records may use a system actor or development actor placeholder. The placeholder must still be represented with structured `actor_type` and `actor_id` fields so later authentication can replace it without changing the audit model.

Service actor API keys are credentials for service actors, not actor identities.
API key rotation must not change the stable `actor_id`; it should only change
which key versions can authenticate that service actor.

## Service Actor Registry

Persistent registry foundation for machine integrations that call runtime and
telemetry endpoints.

Suggested service actor fields:

- id;
- actor_id;
- display_name;
- description;
- status;
- owner_type;
- owner_id;
- created_at;
- updated_at.

Allowed service actor statuses:

- active;
- disabled;
- retired.

The registry is disabled by default. With
`AGCP_SERVICE_ACTOR_REGISTRY_ENABLED=true`, runtime and telemetry service actor
authentication can resolve active service actors with active or retiring
non-expired API keys from the registry. Registry-backed actors use persisted
endpoint/action scopes and fine-grained rule records. Config auth remains the
default behavior when the registry flag is disabled.

## Audit Log

Append-only record for governance-relevant changes.

Suggested fields:

- id;
- event_type;
- actor_type;
- actor_id;
- entity_type;
- entity_id;
- summary;
- metadata;
- created_at.

Examples:

- agent_created;
- agent_updated;
- capability_created;
- capability_updated;
- capability_status_changed;
- source_created;
- source_updated;
- source_status_changed;
- data_usage_profile_created;
- data_usage_profile_updated;
- data_usage_profile_review_status_changed;
- model_asset_created;
- model_asset_updated;
- model_asset_status_changed;
- access_grant_created;
- access_grant_updated;
- access_grant_status_changed;
- policy_created;
- policy_updated;
- policy_status_changed;
- policy_rule_created;
- policy_rule_updated;
- check_tool_registered;
- policy_check_result_recorded;
- policy_check_run_recorded;
- policy_decision_recorded;
- human_approval_requested;
- human_approval_approved;
- human_approval_rejected;
- evidence_bundle_exported;
- evidence_bundle_export_denied;
- runtime_tool_call_resume_checked;
- service_actor_key_created;
- service_actor_key_rotated;
- service_actor_key_revoked;
- service_actor_key_auth_failed;
- service_actor_created;
- service_actor_disabled;
- service_actor_retired;
- service_actor_scope_granted;
- service_actor_scope_revoked.

Audit metadata must contain only safe, non-sensitive context. Do not store raw prompts, credentials, tokens, secrets, private customer data, or raw sensitive payloads in audit metadata.

## Human Approval

A human decision required by policy or workflow.

Allowed statuses:

- pending;
- approved;
- rejected;
- expired;
- cancelled.

Suggested fields:

- id;
- agent_id;
- policy_decision_id;
- status;
- requested_by_actor_type;
- requested_by_actor_id;
- reviewed_by_actor_type;
- reviewed_by_actor_id;
- reason;
- decision_note;
- created_at;
- reviewed_at;
- expires_at.

## Evidence Bundle

An exportable package of records supporting review or audit.

Initial format:

- JSON.

The JSON export includes Agent metadata, related AuditLogs, AgentRunRecords,
TraceEventRecords, PolicyDecisions, HumanApprovals, Agent-scoped Access Grants,
safe references to granted Capability, Source, and ModelAsset targets, and safe
Data Usage Profile summaries for granted Sources when available. Access Grant,
inventory, and Data Usage Profile records are declarative evidence only; they
do not imply that Runtime Gateway policy evaluation currently enforces the
grant or certifies legal usability.

Current export access is intentionally narrow: `auditor`, `platform_admin`, and
direct user owners can export. Direct owner access means a user actor whose
`actor_id` matches an Agent with `owner_type = "user"` and the same `owner_id`.
Team, service, and organization-unit ownership require a future resolver and
are not implemented yet.

Later:

- PDF;
- signed archive;
- integration with GRC tools.
