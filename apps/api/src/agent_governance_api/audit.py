from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from agent_governance_api.metadata_safety import reject_unsafe_metadata_keys
from agent_governance_api.models import ActorType, AuditLog

AuditMetadataValue = str | int | float | bool | None
AuditMetadata = Mapping[str, AuditMetadataValue]

__all__ = ["append_audit_log"]


def append_audit_log(
    session: Session,
    *,
    event_type: str,
    actor_type: ActorType,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    summary: str,
    metadata: AuditMetadata | None = None,
) -> AuditLog:
    safe_metadata = reject_unsafe_metadata_keys(
        dict(metadata or {}),
        error_message="Audit metadata contains unsafe key names.",
    )

    audit_log = AuditLog(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        metadata_=safe_metadata,
        created_at=datetime.now(UTC),
    )
    session.add(audit_log)
    session.flush()

    return audit_log
