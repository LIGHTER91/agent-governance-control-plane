# HumanApproval RBAC Design

## Status

Design proposal only. The current backend has HumanApproval persistence,
explicit transition endpoints, ActorContext-based requester and reviewer fields,
and AuditLog records for create, approve, reject, and cancel actions. It does
not yet enforce RBAC, separation of duties, team membership, or enterprise user
authentication.

The current local development actor remains:

```text
actor_type = "development"
actor_id = "dev-placeholder"
```

That actor is acceptable only for local development and tests. Production review
actions need a real actor identity and authorization checks before HumanApproval
records can be used as meaningful governance evidence.

AGCP remains an Agent Governance Control Plane. HumanApproval RBAC should govern
who may review or administer approval records; it should not turn AGCP into an
orchestrator, workflow engine, or identity provider.

## Why HumanApproval Review Needs RBAC

HumanApproval is the point where AGCP records human oversight for policy
decisions that cannot be handled by deterministic policy alone. Approve, reject,
and cancel are privileged actions because they affect whether a blocked or
escalated action may later proceed through a wrapper or adapter.

Without RBAC:

- any authenticated actor could approve sensitive actions;
- a service actor could approve the same action it requested;
- an Agent owner could bypass independent review for production or high-risk
  actions;
- auditors could mutate the evidence they are meant to inspect;
- Evidence Bundles would show actor fields, but not prove the actor was allowed
  to perform the review.

V1 RBAC should be simple, explicit, and scoped to the existing HumanApproval
workflow.

## Current HumanApproval API Surface

Existing endpoints:

- `POST /human-approvals`
- `GET /human-approvals/{approval_id}`
- `GET /agents/{agent_id}/human-approvals`
- `POST /human-approvals/{approval_id}/approve`
- `POST /human-approvals/{approval_id}/reject`
- `POST /human-approvals/{approval_id}/cancel`

Existing transition rules:

- create always creates `pending`;
- approve, reject, and cancel require `pending`;
- approve and reject set reviewer actor fields and `reviewed_at`;
- all mutations append AuditLog records.

RBAC should preserve these transition rules and add authorization before
mutation.

## Relevant Roles

| Role | Purpose |
| --- | --- |
| `reviewer` | Human reviewer allowed to approve or reject approvals within assigned scope. |
| `agent_owner` | Accountable owner or owner delegate for one or more Agents. |
| `policy_admin` | User who manages Policies and Policy Rules and can inspect policy-linked approvals. |
| `auditor` | Read-only reviewer of governance evidence and approval history. |
| `platform_admin` | Administrative actor with broad operational authority, still fully audited. |

Service actors are intentionally not listed as HumanApproval reviewers. Runtime
and telemetry integrations can request review, but they should not approve or
reject it by default.

## Allowed Actions

HumanApproval RBAC should cover these action families:

- view pending approvals;
- approve a pending approval;
- reject a pending approval;
- cancel a pending approval;
- view approval history.

These actions should be checked separately. For example, an auditor can view
approval history but cannot approve or reject. A requester may be allowed to
cancel a pending approval but not approve it.

## Initial V1 Permission Model

| Action | reviewer | agent_owner | policy_admin | auditor | platform_admin |
| --- | --- | --- | --- | --- | --- |
| View pending approvals | Scoped | Scoped owned Agents | Scoped policy-linked approvals | Yes, read-only | Yes |
| Approve | Scoped assigned or allowed approvals | No by default | No by default | No | Yes, audited |
| Reject | Scoped assigned or allowed approvals | No by default | No by default | No | Yes, audited |
| Cancel | No by default unless requester | Requester only if allowed | No by default | No | Yes, audited |
| View approval history | Scoped | Scoped owned Agents | Scoped policy-linked approvals | Yes, read-only | Yes |

V1 should treat `platform_admin` approval as a break-glass or delegated
administrative action, not as the ordinary review path. It should be audited
with the same HumanApproval event records and later may need a reason code.

## Separation Of Duties

V1 should enforce a few concrete separation-of-duties rules before adding a
complex enterprise permission model:

- The actor that requested a HumanApproval should not approve or reject the same
  approval by default.
- Service actors should not approve, reject, or cancel HumanApprovals by
  default.
- The development actor may approve, reject, or cancel only in local/dev mode so
  tests and demos remain deterministic.
- A policy admin should not automatically approve exceptions to policies they
  manage.
- An Agent owner should not automatically approve production or high-risk
  actions for their own Agent unless an explicit organization rule permits it.
- Platform admin override should be rare, explicit, and auditable.

These rules should be enforced after actor identity is resolved and before the
HumanApproval status is changed.

## Ownership And Scope Checks

RBAC decisions should use structured relationships already present in the
domain model before adding heavier identity infrastructure.

### HumanApproval.agent_id

Every HumanApproval belongs to an Agent. V1 checks should load the Agent and use
the approval's `agent_id` as the primary resource boundary.

Useful checks:

- reviewer is assigned to this Agent or an allowed Agent set;
- agent owner is allowed only for owned Agents;
- auditor can read across allowed environments or assigned review scope.

### Agent.owner_type And Agent.owner_id

Agent ownership answers who is accountable for the Agent. It should support
scoped visibility and future owner-based approval policy.

Existing owner conventions:

```text
owner_type = "user"              -> owner_id = "user:<external-id>"
owner_type = "team"              -> owner_id = "team:<slug>"
owner_type = "service"           -> owner_id = "service:<slug>"
owner_type = "organization_unit" -> owner_id = "org_unit:<slug>"
```

V1 should avoid deep team resolution. A local resolver can start with direct
user ownership and explicit test mappings, then later use identity-provider
claims or directory data for team and organization-unit membership.

### PolicyDecision.policy_id And rule_id

Many approvals are linked to a PolicyDecision. When present, the linked
PolicyDecision can support policy-related visibility:

- policy admins can view approvals linked to policies they administer;
- reviewers can be scoped to policy families or risk categories later;
- approval evidence can show which Policy and Policy Rule caused the review.

Policy linkage should not automatically grant mutation rights. Viewing a
policy-linked approval is different from approving it.

### Future Team Membership Resolution

Team and organization-unit ownership should remain future work until the
identity provider model is clearer.

Recommended V1 direction:

1. Use direct actor ID and role checks first.
2. Support explicit local mappings in tests and development.
3. Add team membership resolver behind a small interface later.
4. Avoid embedding identity-provider-specific claims in HumanApproval models.

## Audit Expectations

Every HumanApproval mutation must remain audited.

For approve, reject, and cancel:

- AuditLog must include the actor's `actor_type` and `actor_id`;
- HumanApproval reviewer fields must include the auth-derived actor for approve
  and reject;
- cancel should record the actor in AuditLog even if reviewer fields remain
  unset;
- denied attempts should be auditable later where safe;
- audit metadata must not include raw prompts, raw tool payloads, credentials,
  authorization headers, API keys, or private customer data.

`decision_note` and `reason` are human-entered text. They should describe the
review rationale, not contain sensitive payloads. V1 should document this
clearly, and a later hardening task may add validation or redaction for unsafe
terms if needed.

Denied authorization attempts should use safe metadata only, for example:

```json
{
  "approval_id": "approval-id",
  "agent_id": "agent-id",
  "action": "approve",
  "denial_reason": "missing_reviewer_role"
}
```

Denied-attempt audit logging should not include raw request bodies, raw API
keys, or sensitive notes.

## Minimal Implementation Path

1. Make ActorContext role-aware.
   - Continue using the existing ActorContext boundary.
   - Treat `roles` as the first local role source.
   - Keep service actor scopes separate from human RBAC roles where possible.
2. Add a local/dev reviewer role stub.
   - In local/dev, allow `development/dev-placeholder` to carry enough role
     context for tests and demo flows.
   - Do not present this as production auth.
3. Require reviewer or platform_admin for approve/reject.
   - Check status is pending as today.
   - Check actor role and scope before mutating the approval.
   - Reject service actors by default.
4. Allow cancel only by requester or platform_admin initially.
   - A requester can cancel a still-pending approval they created.
   - Platform admin can cancel with clear audit evidence.
   - Reviewer cancel can remain future work unless a real workflow requires it.
5. Add tests.
   - reviewer can approve assigned or allowed approval;
   - reviewer can reject assigned or allowed approval;
   - auditor can view but not mutate;
   - agent_owner can view owned Agent approvals;
   - requester cannot approve their own approval;
   - service actor cannot review by default;
   - development actor behavior remains local/dev only;
   - denied mutations create no status change and no misleading approval audit.

## Recommended Follow-up Issues

1. Add local role-aware ActorContext support for human users.
2. Add HumanApproval RBAC checks for approve and reject.
3. Add HumanApproval cancel authorization for requester and platform admin.
4. Add scoped read checks for `GET /human-approvals/{approval_id}`.
5. Add scoped read checks for `GET /agents/{agent_id}/human-approvals`.
6. Add separation-of-duties check preventing requester self-approval.
7. Add safe denied-authorization audit events for HumanApproval review actions.
8. Add tests proving service actors cannot approve or reject by default.
9. Design team membership resolution for Agent ownership checks.
10. Align Evidence Bundle export RBAC with HumanApproval visibility rules.

## Open Questions

- Should `agent_owner` ever approve low-risk approvals for owned Agents, or
  should review always require a separate reviewer role?
- Should `cancel` be requester-only, reviewer-only, or both?
- Should platform admin review require a mandatory reason or break-glass note?
- Should denied review attempts be audited immediately, or only in strict
  production auth mode?
- How should reviewer assignment be represented before there are users, teams,
  and role tables?
