# Security and Privacy Guardrails

## Security stance

This product will handle sensitive metadata about AI agents, actions, tools, data access, and policy decisions.

Security is part of the product, not an add-on.

## Do not store secrets

Never store:

- API keys;
- OAuth tokens;
- passwords;
- private keys;
- raw credentials;
- unredacted authorization headers.

## Logging rules

Logs must not contain:

- credentials;
- raw sensitive prompts;
- raw user files;
- full customer records;
- protected attributes;
- access tokens;
- internal secrets.

## Audit log rule

Audit logs should capture governance-relevant facts, not sensitive payloads.

Example:

Good:

```json
{
  "event_type": "tool_access_denied",
  "agent_id": "agent_123",
  "tool_name": "send_email",
  "decision": "deny",
  "policy_id": "policy_456"
}
```

Bad:

```json
{
  "full_prompt": "...contains private customer data...",
  "api_key": "sk-..."
}
```

## Access control principle

Start simple, but design for future RBAC.

Initial roles may eventually include:

- admin;
- platform_engineer;
- agent_owner;
- reviewer;
- auditor;
- read_only.

Do not implement complex RBAC before it is required.

## Threats to keep in mind

- prompt injection causing unsafe tool calls;
- agent using unauthorized data;
- missing audit evidence;
- policy bypass through direct API calls;
- logs leaking sensitive data;
- shadow agents not registered;
- excessive permissions;
- unreviewed production promotion;
- malicious or accidental policy changes.

## Required future controls

- SSO;
- RBAC;
- audit log integrity;
- retention policies;
- export controls;
- policy versioning;
- incident review;
- secret redaction;
- data minimization.
