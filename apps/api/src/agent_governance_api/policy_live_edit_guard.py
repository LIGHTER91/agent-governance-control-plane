from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_governance_api.audit import append_audit_log
from agent_governance_api.auth import ActorContext
from agent_governance_api.models import PolicyVersion, PolicyVersionStatus

POLICY_LIVE_EDIT_BLOCKED_DETAIL = (
    "Direct live Policy edits are disabled for policies with an active "
    "PolicyVersion. Create a draft PolicyVersion and submit it for review."
)
POLICY_RULE_LIVE_EDIT_BLOCKED_DETAIL = (
    "Direct live PolicyRule edits are disabled for policies with an active "
    "PolicyVersion. Create a draft PolicyVersion and submit it for review."
)


def active_policy_version_for_policy(
    session: Session,
    policy_id: UUID,
) -> PolicyVersion | None:
    return session.scalar(
        select(PolicyVersion)
        .where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.status == PolicyVersionStatus.ACTIVE,
        )
        .order_by(PolicyVersion.version_number, PolicyVersion.id)
    )


def block_policy_live_edit_if_active_version_exists(
    session: Session,
    *,
    policy_id: UUID,
    actor: ActorContext,
    operation: str,
    entity_type: str,
    entity_id: str,
    detail: str,
) -> None:
    active_version = active_policy_version_for_policy(session, policy_id)
    if active_version is None:
        return

    append_audit_log(
        session,
        event_type="policy_live_edit_blocked",
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        summary="Legacy live Policy mutation blocked.",
        metadata={
            "operation": operation,
            "policy_id": str(policy_id),
            "active_policy_version_id": str(active_version.id),
            "active_policy_version_number": active_version.version_number,
            "reason": detail,
        },
    )
    session.commit()
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
