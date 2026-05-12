# Risk Register

## R1 — Product too broad

Risk:
The product becomes a generic AI governance platform without a clear core.

Mitigation:
Keep the center of gravity on runtime-oriented agent governance: registry, policies, decisions, audit, evidence.

## R2 — Codex over-engineering

Risk:
Codex introduces microservices, event streaming, complex RBAC, OPA, or unnecessary dependencies.

Mitigation:
Use AGENTS.md, small issues, PR review, and explicit non-goals.

## R3 — Compliance overclaiming

Risk:
The product claims to make customers compliant with AI Act, ISO 42001, or other frameworks.

Mitigation:
Use evidence/support language only.

## R4 — Observability clone

Risk:
The product becomes just another tracing/debugging tool.

Mitigation:
Focus on "was this allowed?" not only "what happened?"

## R5 — Weak audit integrity

Risk:
Audit logs can be modified or deleted through normal APIs.

Mitigation:
Design append-only audit APIs and test immutability.

## R6 — Integration explosion

Risk:
Too many frameworks are supported too early.

Mitigation:
Start with generic HTTP ingestion, then one concrete integration.

## R7 — Sensitive data leakage

Risk:
Traces or logs store private payloads.

Mitigation:
Redaction, minimal schemas, context hashes, and explicit logging rules.

## R8 — No buyer urgency

Risk:
The product is useful but not urgent enough to buy.

Mitigation:
Validate with teams already deploying production agents and facing review/security/compliance pressure.
