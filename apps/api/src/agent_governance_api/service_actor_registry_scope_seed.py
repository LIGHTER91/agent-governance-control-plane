from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.config import (
    ServiceActorScopeRule as ConfigServiceActorScopeRule,
)
from agent_governance_api.config import (
    ServiceActorScopes as ConfigServiceActorScopes,
)
from agent_governance_api.config import Settings
from agent_governance_api.models import (
    ServiceActor,
    ServiceActorScope,
    ServiceActorScopeRule,
)

ScopeRuleKey: TypeAlias = tuple[
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]


class ScopeSeedAction(StrEnum):
    CREATE = "create"
    EXISTS = "exists"
    DRY_RUN_CREATE = "dry_run_create"
    MISSING_ACTOR = "missing_actor"


@dataclass(frozen=True)
class ScopeSeedScopeResult:
    actor_id: str
    scope: str
    action: ScopeSeedAction


@dataclass(frozen=True)
class ScopeSeedRuleResult:
    actor_id: str
    action: ScopeSeedAction
    agent_ids_count: int
    environments_count: int
    runtime_modes_count: int
    tool_names_count: int


@dataclass(frozen=True)
class ScopeSeedResults:
    scopes: tuple[ScopeSeedScopeResult, ...]
    rules: tuple[ScopeSeedRuleResult, ...]


def seed_service_actor_registry_scopes_from_settings(
    session: Session,
    settings: Settings,
    *,
    dry_run: bool = True,
) -> ScopeSeedResults:
    """Seed persisted service actor scopes and rules from safe config values.

    Existing persisted records are preserved. This helper creates missing
    endpoint/action scope rows and appends non-duplicate fine-grained rule rows.
    It never reads or writes raw API keys.
    """

    scope_results = _seed_scope_records(
        session,
        settings.service_actor_scopes,
        dry_run=dry_run,
    )
    rule_results = _seed_rule_records(
        session,
        settings.service_actor_scope_rules,
        dry_run=dry_run,
    )

    if not dry_run:
        session.commit()

    return ScopeSeedResults(
        scopes=tuple(scope_results),
        rules=tuple(rule_results),
    )


def format_scope_seed_results(results: ScopeSeedResults, *, dry_run: bool) -> str:
    if not results.scopes and not results.rules:
        return (
            "No AGCP_SERVICE_ACTOR_SCOPES or AGCP_SERVICE_ACTOR_SCOPE_RULES "
            "entries found. Nothing to seed."
        )

    mode = "DRY RUN" if dry_run else "APPLIED"
    lines = [
        f"{mode}: service actor registry scope seed results",
        "Existing persisted scope and rule records are preserved.",
        "Raw API keys are not read, logged, or persisted by this helper.",
    ]
    for result in results.scopes:
        lines.append(
            " - "
            f"scope actor_id={result.actor_id} "
            f"scope={result.scope} "
            f"action={result.action.value}"
        )
    for result in results.rules:
        lines.append(
            " - "
            f"rule actor_id={result.actor_id} "
            f"action={result.action.value} "
            f"agent_ids_count={result.agent_ids_count} "
            f"environments_count={result.environments_count} "
            f"runtime_modes_count={result.runtime_modes_count} "
            f"tool_names_count={result.tool_names_count}"
        )
    return "\n".join(lines)


def _seed_scope_records(
    session: Session,
    configured_scopes: tuple[ConfigServiceActorScopes, ...],
    *,
    dry_run: bool,
) -> list[ScopeSeedScopeResult]:
    results: list[ScopeSeedScopeResult] = []
    planned_scope_keys: set[tuple[str, str]] = set()

    for entry in configured_scopes:
        actor = _service_actor_by_actor_id(session, entry.actor_id)
        existing_scopes = _scope_values_for_actor(session, actor) if actor else set()

        for scope in entry.scopes:
            if actor is None:
                results.append(
                    ScopeSeedScopeResult(
                        actor_id=entry.actor_id,
                        scope=scope,
                        action=ScopeSeedAction.MISSING_ACTOR,
                    )
                )
                continue

            scope_key = (entry.actor_id, scope)
            if scope in existing_scopes or scope_key in planned_scope_keys:
                action = ScopeSeedAction.EXISTS
            else:
                action = (
                    ScopeSeedAction.DRY_RUN_CREATE
                    if dry_run
                    else ScopeSeedAction.CREATE
                )
                planned_scope_keys.add(scope_key)
                existing_scopes.add(scope)
                if not dry_run:
                    session.add(ServiceActorScope(service_actor=actor, scope=scope))

            results.append(
                ScopeSeedScopeResult(
                    actor_id=entry.actor_id,
                    scope=scope,
                    action=action,
                )
            )

    return results


def _seed_rule_records(
    session: Session,
    configured_rules: tuple[ConfigServiceActorScopeRule, ...],
    *,
    dry_run: bool,
) -> list[ScopeSeedRuleResult]:
    results: list[ScopeSeedRuleResult] = []
    planned_rule_keys: set[ScopeRuleKey] = set()

    for rule in configured_rules:
        actor = _service_actor_by_actor_id(session, rule.actor_id)
        action = ScopeSeedAction.MISSING_ACTOR

        if actor is not None:
            rule_key = _rule_key(rule.actor_id, rule)
            rule_exists = _matching_rule_exists(session, actor, rule)
            if rule_exists or rule_key in planned_rule_keys:
                action = ScopeSeedAction.EXISTS
            else:
                action = (
                    ScopeSeedAction.DRY_RUN_CREATE
                    if dry_run
                    else ScopeSeedAction.CREATE
                )
                planned_rule_keys.add(rule_key)
                if not dry_run:
                    session.add(
                        ServiceActorScopeRule(
                            service_actor=actor,
                            agent_ids=list(rule.agent_ids),
                            environments=list(rule.environments),
                            runtime_modes=list(rule.runtime_modes),
                            tool_names=list(rule.tool_names),
                        )
                    )

        results.append(
            ScopeSeedRuleResult(
                actor_id=rule.actor_id,
                action=action,
                agent_ids_count=len(rule.agent_ids),
                environments_count=len(rule.environments),
                runtime_modes_count=len(rule.runtime_modes),
                tool_names_count=len(rule.tool_names),
            )
        )

    return results


def _service_actor_by_actor_id(session: Session, actor_id: str) -> ServiceActor | None:
    return session.scalar(select(ServiceActor).where(ServiceActor.actor_id == actor_id))


def _scope_values_for_actor(
    session: Session,
    actor: ServiceActor,
) -> set[str]:
    return set(
        session.scalars(
            select(ServiceActorScope.scope).where(
                ServiceActorScope.service_actor_id == actor.id
            )
        ).all()
    )


def _matching_rule_exists(
    session: Session,
    actor: ServiceActor,
    rule: ConfigServiceActorScopeRule,
) -> bool:
    desired_key = _rule_key(actor.actor_id, rule)
    existing_rules = session.scalars(
        select(ServiceActorScopeRule).where(
            ServiceActorScopeRule.service_actor_id == actor.id
        )
    ).all()
    return any(
        _persisted_rule_key(actor.actor_id, existing_rule) == desired_key
        for existing_rule in existing_rules
    )


def _rule_key(
    actor_id: str,
    rule: ConfigServiceActorScopeRule,
) -> ScopeRuleKey:
    return (
        actor_id,
        tuple(sorted(rule.agent_ids)),
        tuple(sorted(rule.environments)),
        tuple(sorted(rule.runtime_modes)),
        tuple(sorted(rule.tool_names)),
    )


def _persisted_rule_key(
    actor_id: str,
    rule: ServiceActorScopeRule,
) -> ScopeRuleKey:
    return (
        actor_id,
        tuple(sorted(rule.agent_ids)),
        tuple(sorted(rule.environments)),
        tuple(sorted(rule.runtime_modes)),
        tuple(sorted(rule.tool_names)),
    )
