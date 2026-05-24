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

A source of information the agent can access.

Examples:

- internal_docs;
- customer_records;
- HR_data;
- support_tickets;
- vector_database;
- SharePoint;
- Dataiku dataset.

## Model

A model or model endpoint used by an agent.

Fields may include:

- provider;
- model_name;
- endpoint_alias;
- deployment_environment.

Do not store secrets.

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
  "risk_level": "low"
}
```

Required fields:

- `decision`: one of `allow`, `deny`, `require_human_review`, or `not_applicable`;
- `reason`: non-empty human-readable explanation.

Optional matching fields:

- `agent_id`;
- `tool_name`;
- `environment`: one of `development`, `staging`, or `production`;
- `risk_level`: one of `low`, `medium`, `high`, or `critical`.

Unsupported condition fields must be rejected rather than interpreted implicitly.

Suggested fields:

- id;
- policy_id;
- name;
- description;
- condition;
- created_at;
- updated_at.

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

Trace event metadata must contain only safe, non-sensitive context. Do not store raw prompts, credentials, tokens, secrets, authorization headers, or raw sensitive payloads in telemetry metadata.

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
- policy_created;
- policy_updated;
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

Current export access is intentionally narrow: `auditor`, `platform_admin`, and
direct user owners can export. Direct owner access means a user actor whose
`actor_id` matches an Agent with `owner_type = "user"` and the same `owner_id`.
Team, service, and organization-unit ownership require a future resolver and
are not implemented yet.

Later:

- PDF;
- signed archive;
- integration with GRC tools.
