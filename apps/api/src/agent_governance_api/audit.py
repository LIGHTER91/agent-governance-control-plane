from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from agent_governance_api.models import ActorType, AuditLog

AuditMetadataValue = str | int | float | bool | None
AuditMetadata = Mapping[str, AuditMetadataValue]

SENSITIVE_METADATA_KEY_PARTS = (
    "api_key",
    "credential",
    "password",
    "payload",
    "private_customer_data",
    "raw_prompt",
    "secret",
    "access_token",
    "refresh_token",
)

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
    safe_metadata = dict(metadata or {})
    _ensure_safe_metadata_keys(safe_metadata)

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


def _ensure_safe_metadata_keys(metadata: AuditMetadata) -> None:
    unsafe_keys = [
        key
        for key in metadata
        if any(part in key.lower() for part in SENSITIVE_METADATA_KEY_PARTS)
    ]
    if unsafe_keys:
        raise ValueError("Audit metadata contains unsafe key names.")
