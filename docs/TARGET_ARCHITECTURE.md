# Target Architecture

## Long-term conceptual architecture

```text
AI Agents / Agentic Apps
  |
  | SDK / Middleware / Runtime Gateway / Event Collector
  v
Agent Governance Control Plane
  |
  +-- Agent Registry
  +-- Policy Engine
  +-- Runtime Decision Layer
  +-- Audit Trail
  +-- Human Oversight
  +-- Evidence Center
  +-- Risk Monitoring
  +-- Integration Hub
  |
  v
Storage
  +-- PostgreSQL: canonical domain entities
  +-- Event store / analytical DB later: traces and high-volume events
  +-- Object storage later: evidence bundles and exports
```

## Initial implementation architecture

```text
apps/api
  FastAPI application
  REST endpoints
  domain services
  persistence adapters

packages/domain
  core domain models
  enums
  validation rules

packages/audit
  audit log domain and services

packages/policy
  policy model and basic evaluator

packages/telemetry
  agent run event schema
  ingestion DTOs

apps/web
  reserved for future dashboard
```

## Initial data flow

```text
1. User creates Agent in Registry.
2. API validates Agent metadata.
3. Agent is stored.
4. AuditLog is created for the mutation.
5. Later, agent runs emit events.
6. Events are stored as telemetry records.
7. Policy evaluator creates PolicyDecision records.
8. Evidence export collects agent, policies, decisions, audit logs.
```

## Future runtime control path

```text
Agent wants to call a tool
  ↓
Runtime Gateway receives action request
  ↓
Policy Engine evaluates context
  ↓
Decision:
  - allow
  - deny
  - require_human_review
  ↓
Decision and evidence are stored
  ↓
Agent receives response or escalation
```
