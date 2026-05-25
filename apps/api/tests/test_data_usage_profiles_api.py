from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import ActorType, AuditLog

SessionFactory = Callable[[], Session]


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db_session() -> Iterator[Session]:
        with testing_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_create_source_usage_profile(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)

    response = client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["source_id"] == source_id
    assert body["data_classification"] == "confidential"
    assert body["contains_personal_data"] is True
    assert body["contains_sensitive_data"] is False
    assert body["data_categories"] == ["customer_data", "financial_data"]
    assert body["allowed_purposes"] == ["customer_support_answering"]
    assert body["prohibited_purposes"] == ["training_data_generation"]
    assert body["allowed_processing"] == ["search", "rag"]
    assert body["prohibited_processing"] == ["training"]
    assert body["review_status"] == "approved"
    assert body["dpia_required"] is True
    assert body["metadata"] == {"catalog_ref": "catalog:source-123"}
    assert "metadata_" not in body


def test_get_source_usage_profile(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)
    created = client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.get(f"/sources/{source_id}/usage-profile")

    assert response.status_code == 200
    assert response.json()["id"] == created.json()["id"]
    assert response.json()["source_id"] == source_id


def test_update_source_usage_profile(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)
    client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.patch(
        f"/sources/{source_id}/usage-profile",
        json={
            "allowed_purposes": ["customer_support_answering", "incident_triage"],
            "metadata": {"catalog_ref": "catalog:source-123", "review": "refreshed"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed_purposes"] == [
        "customer_support_answering",
        "incident_triage",
    ]
    assert body["metadata"] == {
        "catalog_ref": "catalog:source-123",
        "review": "refreshed",
    }


def test_empty_source_usage_profile_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)
    client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.patch(f"/sources/{source_id}/usage-profile", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_duplicate_source_usage_profile_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)
    client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Data usage profile already exists for source."


def test_source_usage_profile_source_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_source_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        f"/sources/{missing_source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found."


def test_source_usage_profile_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)

    response = client.get(f"/sources/{source_id}/usage-profile")

    assert response.status_code == 404
    assert response.json()["detail"] == "Data usage profile not found."


def test_source_usage_profile_create_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)

    response = client.post(
        f"/sources/{source_id}/usage-profile",
        json={
            **data_usage_profile_payload(),
            "metadata": {"raw_prompt_ref": "do-not-store"},
        },
    )

    assert response.status_code == 422


def test_source_usage_profile_update_rejects_unsafe_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    source_id = create_source(client)
    client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.patch(
        f"/sources/{source_id}/usage-profile",
        json={"metadata": {"scanner_payload_ref": "do-not-store"}},
    )

    assert response.status_code == 422


def test_audit_log_created_on_source_usage_profile_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    source_id = create_source(client)

    response = client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    assert response.status_code == 201
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "data_usage_profile_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "data_usage_profile"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "operation": "create",
        "source_id": source_id,
        "data_classification": "confidential",
        "review_status": "approved",
        "contains_personal_data": True,
        "contains_sensitive_data": False,
        "dpia_required": True,
    }
    assert "allowed_purposes" not in str(audit_log.metadata_)


def test_audit_log_created_on_source_usage_profile_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    source_id = create_source(client)
    client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.patch(
        f"/sources/{source_id}/usage-profile",
        json={"metadata": {"catalog_ref": "catalog:source-123", "review": "updated"}},
    )

    assert response.status_code == 200
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "data_usage_profile_updated"
    assert audit_log.entity_type == "data_usage_profile"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "source_id": source_id,
        "updated_fields": "metadata",
    }
    assert "catalog_ref" not in str(audit_log.metadata_)


def test_audit_log_created_on_source_usage_profile_review_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    source_id = create_source(client)
    client.post(
        f"/sources/{source_id}/usage-profile",
        json=data_usage_profile_payload(),
    )

    response = client.patch(
        f"/sources/{source_id}/usage-profile",
        json={"review_status": "needs_review"},
    )

    assert response.status_code == 200
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "data_usage_profile_review_status_changed"
    assert audit_log.entity_type == "data_usage_profile"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "source_id": source_id,
        "updated_fields": "review_status",
        "review_status_from": "approved",
        "review_status_to": "needs_review",
    }


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def create_source(client: TestClient) -> str:
    response = client.post("/sources", json=source_payload())
    assert response.status_code == 201
    return str(response.json()["id"])


def source_payload() -> dict[str, object]:
    return {
        "name": "Support knowledge base",
        "description": "Governed source for support runbooks.",
        "source_type": "knowledge_base",
        "external_ref": "kb:support-runbooks",
        "owner_type": "team",
        "owner_id": "team:support-ops",
        "owner_name": "Support Operations",
        "owner_contact_email": "support-ops@example.invalid",
        "status": "active",
        "risk_level": "medium",
        "metadata": {"domain": "support", "system": "runbook_index"},
    }


def data_usage_profile_payload() -> dict[str, object]:
    return {
        "data_classification": "confidential",
        "contains_personal_data": True,
        "contains_sensitive_data": False,
        "data_categories": ["customer_data", "financial_data"],
        "legal_basis": "declared_contractual_basis",
        "allowed_purposes": ["customer_support_answering"],
        "prohibited_purposes": ["training_data_generation"],
        "allowed_processing": ["search", "rag"],
        "prohibited_processing": ["training"],
        "residency": "eu",
        "retention_policy": "retention:standard-support",
        "data_owner": "team:support-ops",
        "review_status": "approved",
        "reviewed_by_actor_type": "user",
        "reviewed_by_actor_id": "user:dpo-1",
        "reviewed_at": "2026-01-15T12:00:00Z",
        "review_expires_at": "2027-01-15T12:00:00Z",
        "dpia_required": True,
        "dpia_reference": "dpia:DPIA-123",
        "metadata": {"catalog_ref": "catalog:source-123"},
    }
