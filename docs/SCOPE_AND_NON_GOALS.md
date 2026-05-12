# Scope and Non-goals

## In scope

Long-term platform scope:

- Agent registry.
- Agent ownership.
- Agent lifecycle.
- Runtime policy decisions.
- Tool/model/data-source declarations.
- Permission model.
- Audit trails.
- Human oversight workflows.
- Risk classification.
- Evidence bundles.
- Incident review.
- Integrations with agent frameworks.
- Integrations with enterprise systems.

## Initial implementation scope

Initial product nucleus:

1. Agent Registry.
2. Immutable Audit Log.
3. Basic Policy and Policy Decision models.
4. Telemetry event schema.
5. Minimal ingestion endpoint for agent run events.
6. Minimal dashboard later.

## Out of scope for initial development

Do not build these in the first implementation phase:

- full compliance management platform;
- complex GRC workflows;
- agent orchestration;
- prompt engineering workbench;
- multi-agent execution engine;
- marketplace of agents;
- automatic legal compliance scoring;
- AI Act certification workflow;
- ISO 42001 certification workflow;
- complex RBAC;
- Kubernetes operator;
- microservice architecture;
- LLM-as-policy-engine.

## Strategic non-goals

The product should not become:

- "LangSmith clone";
- "n8n clone";
- "Dataiku replacement";
- "LangGraph alternative";
- "generic AI governance checklist tool";
- "dashboard with compliance buzzwords".

## Product center of gravity

The center of gravity is:

> Runtime-oriented governance of AI agents through registry, policies, decisions, audit trails, and evidence.
