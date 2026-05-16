# [Codex] Add PolicyRule adapter for persisted rules

Status: Completed in V0 backend milestone.

## Objective

Convert persisted active `PolicyRule` records into deterministic evaluator
rules.

## Context

The policy evaluator originally consumed explicit in-memory rule DTOs. Persisted
policy rules needed a narrow adapter before policy evaluation could use database
state.

## Completed scope

- Added a service/module that loads active `Policy` and `PolicyRule` records.
- Converted supported rule condition fields into evaluator DTOs.
- Supported explicit matching fields:
  - `agent_id`
  - `tool_name`
  - `environment`
  - `risk_level`
- Rejected unsupported condition fields clearly.
- Added tests for allow, deny, require human review, inactive policies, invalid
  conditions, and evaluator precedence.

## Non-goals preserved

- No Policy CRUD API.
- No OPA, Rego, Cedar, LLM-based policy decisions, or runtime blocking.

## Validation

Covered by policy rule adapter tests in the completed V0 backend milestone.
