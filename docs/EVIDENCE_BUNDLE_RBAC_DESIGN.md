# Evidence Bundle RBAC Design

## Status

Design plus minimal V1 implementation. The current backend exports a JSON
Evidence Bundle for a single Agent through:

```text
GET /agents/{agent_id}/evidence-bundle
```

The current export includes Agent metadata, related AuditLogs, Agent runs, Trace
Events, PolicyDecisions, HumanApprovals, and Policy or PolicyRule references
when available. Metadata is filtered before export. The endpoint now enforces a
minimal RBAC check that allows actors with `auditor` or `platform_admin` roles,
plus direct user owners whose `actor_id` matches the Agent `owner_id`.
Successful JSON exports append a safe `evidence_bundle_exported` AuditLog event.
Denied exports for known Agents append a safe `evidence_bundle_export_denied`
AuditLog event. Service actors are denied by default.

The current implementation still does not enforce team membership,
organization-unit ownership, service ownership, or policy-linked visibility.

AGCP remains an Agent Governance Control Plane. Evidence Bundle RBAC should
control who can inspect governance evidence. It should not turn AGCP into an
orchestrator, compliance certification product, or broad enterprise IAM system.

## Why Evidence Bundle Export Needs RBAC

An Evidence Bundle is more sensitive than a normal Agent read response. It can
reveal:

- what an Agent did;
- which runtime tool calls were requested;
- which policies allowed, denied, or escalated actions;
- who requested HumanApproval;
- who approved, rejected, or cancelled HumanApproval;
- audit history for Agent and HumanApproval mutations;
- safe metadata about operational events.

Even with metadata filtering, Evidence Bundles expose enough governance context
to require authorization before export. Without RBAC, any caller that can reach
the endpoint could inspect operational history for Agents they do not own or
review.

## Current Export Surface

The current bundle shape includes:

- `agent`;
- `audit_logs`;
- `agent_runs`;
- `trace_events`;
- `policy_decisions`;
- `human_approvals`.

The export filters metadata with the central metadata safety helper. It should
continue to exclude raw prompts, raw payloads, credentials, authorization
headers, API keys, tokens, private customer data, and non-primitive metadata
values.

## Roles And Permissions

| Role | V1 export expectation |
| --- | --- |
| `auditor` | Can export Evidence Bundles within audit scope. Platform-wide audit scope may be acceptable for V1 if explicitly assigned. |
| `agent_owner` | Direct user owners can export Evidence Bundles for owned Agents. Team and organization-unit ownership checks are still future work. |
| `policy_admin` | Can view policy-linked evidence when needed, but should not automatically receive broad export access. |
| `platform_admin` | Can export Evidence Bundles for administration or break-glass review. Successful exports are audited. |
| `viewer` | No export by default. May receive restricted read-only summaries later, not full Evidence Bundles. |

V1 should stay conservative. The current minimal implementation allows:

- `auditor`;
- `platform_admin`;
- direct user owners when `actor.actor_id == agent.owner_id` and
  `agent.owner_type == "user"`.

## Service Actor Behavior

Service actors should not read Evidence Bundles by default.

Runtime adapters and telemetry integrations are allowed to submit governance
events, request decisions, and resume blocked tool calls when explicitly scoped.
That does not imply permission to inspect full evidence exports.

Rules:

- service actors are denied Evidence Bundle export by default;
- `evidence:read` must be explicit if service export is ever allowed;
- `evidence:read` should remain separate from `telemetry:write`,
  `runtime:decision`, and `runtime:resume`;
- service actor access should also require Agent, environment, and possibly
  owner restrictions before any export;
- raw API keys must never appear in export responses, AuditLog metadata, or
  denied-attempt metadata.

V1 should avoid service actor Evidence Bundle export unless a concrete
integration needs it.

## Ownership Checks

### Agent Owner Fields

Agent ownership is represented by:

- `owner_type`;
- `owner_id`;
- `owner_name`;
- `owner_contact_email`.

Existing owner ID conventions:

```text
owner_type = "user"              -> owner_id = "user:<external-id>"
owner_type = "team"              -> owner_id = "team:<slug>"
owner_type = "service"           -> owner_id = "service:<slug>"
owner_type = "organization_unit" -> owner_id = "org_unit:<slug>"
```

For `agent_owner` export, V1 checks direct user ownership only. Team,
service, and organization-unit ownership should wait for a resolver.

### Future Team Membership Resolver

Team membership should not be guessed from the Agent record alone. A future
resolver should answer:

```text
actor -> user id
actor -> team memberships
actor -> organization-unit memberships
actor -> delegated owner scopes
```

Until that exists, owner-based Evidence Bundle export is limited to direct user
owner matches.

### Policy-Linked Visibility

PolicyDecisions in the bundle may reference `policy_id` and `rule_id`.
`policy_admin` may need policy-linked evidence for policies they administer,
but this should be narrower than full export access.

Recommended V1 rule:

- `policy_admin` does not get full bundle export by default;
- future policy-linked read access may expose only decisions and references
  connected to policies they administer;
- full Agent Evidence Bundle export still requires auditor, platform_admin, or
  direct user ownership.

### Platform-Wide Auditor Visibility

Auditors may need broad visibility to review governance evidence. V1 can allow
platform-wide auditor export if the role assignment itself is trusted and
audited by future identity management.

Environment-specific restrictions may be needed later, especially for
production Agents.

## V1 Behavior

Recommended initial behavior:

- `platform_admin` can export;
- `auditor` can export;
- direct user owners can export owned Agents;
- `policy_admin` can view policy-linked evidence later if needed;
- `viewer` cannot export full Evidence Bundles;
- service actors cannot export by default;
- all other actors are denied.

This is intentionally conservative.

## Denied Behavior

Denied export attempts should:

- return `403`;
- avoid revealing whether sensitive nested records exist;
- avoid returning partial bundles;
- avoid exposing raw actor credentials, API keys, request headers, or unsafe
  metadata;
- create a safe denied-export audit event when the Agent is known.

The response should be clear but not overly specific:

```text
Evidence Bundle export is not permitted for this actor.
```

For unknown Agents, the endpoint may continue to return `404`. For known Agents
where the actor lacks export permission, return `403` without disclosing counts
or types of nested records.

Safe denied-attempt audit metadata could include:

```json
{
  "agent_id": "agent-id",
  "reason": "forbidden",
  "export_format": "json"
}
```

It must not include raw prompts, raw payloads, authorization headers, API keys,
tokens, or sensitive nested metadata.

## Security Considerations

### Sensitive Metadata Filtering

Evidence export must keep using central metadata filtering for:

- AuditLog metadata;
- AgentRunRecord metadata;
- TraceEventRecord metadata.

Unsafe keys such as `api_key`, `token`, `password`, `secret`, `authorization`,
`credential`, `raw_prompt`, `raw_payload`, and `private_customer_data` must not
be returned.

### Audit Log Visibility

AuditLogs can reveal who changed an Agent, requested HumanApproval, or reviewed
an approval. This is governance evidence, but it is still sensitive operational
data. RBAC should treat audit visibility as part of Evidence Bundle export, not
as ordinary public metadata.

### Human Approval Visibility

HumanApproval records include requester and reviewer actor IDs plus human-entered
`reason` and `decision_note` fields. Those fields should not contain sensitive
payloads, but export authorization should still restrict who can view them.

### Runtime Trace Visibility

TraceEvents and Agent runs can reveal tool names, runtime mode, correlation IDs,
and high-level action summaries. They must not expose raw prompts or raw tool
payloads. Export RBAC should assume runtime traces are sensitive even after
metadata filtering.

### Service Actor Boundaries

Service actor API keys should remain focused on integration calls. A runtime
adapter with `runtime:decision` or `runtime:resume` should not automatically
receive `evidence:read`.

## Minimal Implementation Path

1. Use existing role-aware ActorContext. Implemented for the minimal V1 check.
   - `ActorContext.roles` already exists and can carry local test roles.
   - Keep this as a local boundary, not full authentication.
2. Require `auditor` or `platform_admin` initially. Implemented.
   - Add an Actor dependency to `GET /agents/{agent_id}/evidence-bundle`.
   - Deny service actors unless they explicitly carry a future allowed export
     role or `evidence:read` behavior is designed.
3. Add direct `agent_owner` checks. Implemented for direct user owners.
   - Use direct `owner_type = "user"` and matching `owner_id`.
   - Add team and organization-unit resolution only after identity direction is
     clearer.
4. Add tests. Implemented for auditor, platform admin, unauthorized actors,
   service actor denial, denied payload shape, authorized `404`, and metadata
   filtering.
   - auditor can export;
   - platform_admin can export;
   - viewer cannot export;
   - service actor cannot export by default;
   - direct user owners can export owned Agents;
   - denied export returns `403` and does not leak nested record details.
5. Add successful export audit events. Implemented.
   - Append `evidence_bundle_exported` with safe metadata after successful
     JSON export.
6. Add safe audit of denied attempts. Implemented for known Agents.
   - Audit denied attempts only with safe metadata.
   - Preserve existing unknown-agent response behavior without creating an
     export audit event.

## Recommended Follow-up Issues

1. Design team and organization-unit membership resolver for ownership checks.
2. Add policy-linked evidence visibility design for `policy_admin`.
3. Add environment-specific export restrictions for production Agents if needed.
4. Decide whether service actors should ever receive explicit `evidence:read`.

## Open Questions

- Should team or organization-unit owners export full bundles by default, or
  only a reduced owner view?
- Should `policy_admin` see full bundles or only policy-linked decisions and
  rules?
- Should service actors ever receive `evidence:read`, or should Evidence Bundle
  export remain human/auditor focused in V1?
- Should production Agents require stricter export roles than development
  Agents?
