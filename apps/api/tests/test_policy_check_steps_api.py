from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    ActorType,
    AuditLog,
    CheckTool,
    CheckToolStatus,
    CheckToolType,
    OwnerType,
)

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


def test_create_policy_check_step(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    check_tool_id = create_check_tool(session_factory)

    response = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(
            policy_rule_id=rule_id,
            check_tool_id=check_tool_id,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["policy_rule_id"] == rule_id
    assert body["check_tool_id"] == check_tool_id
    assert body["check_type"] == "data_usage_profile_status"
    assert body["target_selector"] == "source_ids"
    assert body["required"] is True
    assert body["failure_behavior"] == "require_human_review"
    assert body["min_confidence"] == 0.8
    assert body["status"] == "active"
    assert body["evidence_retention"] == "evidence_bundle"
    assert body["metadata"] == {"purpose": "runtime_metadata_pre_check"}
    assert body["created_at"]
    assert body["updated_at"]


def test_create_policy_check_step_allows_builtin_check_type_without_check_tool(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)

    response = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )

    assert response.status_code == 201
    assert response.json()["check_tool_id"] is None


def test_list_policy_check_steps(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    client.post(
        "/policy-check-steps",
        json={
            **policy_check_step_payload(policy_rule_id=rule_id),
            "check_type": "source_status",
            "target_selector": "source_ids",
        },
    )

    response = client.get("/policy-check-steps")

    assert response.status_code == 200
    assert [step["check_type"] for step in response.json()] == [
        "data_usage_profile_status",
        "source_status",
    ]


def test_get_policy_check_step_by_id(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.get(f"/policy-check-steps/{step_id}")

    assert response.status_code == 200
    assert response.json()["id"] == step_id


def test_list_policy_check_steps_for_rule(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    other_rule_id = create_policy_rule(client, policy_id=policy_id, name="Other rule")
    client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=other_rule_id),
    )

    response = client.get(f"/policy-rules/{rule_id}/check-steps")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["policy_rule_id"] == rule_id


def test_update_policy_check_step(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(
        f"/policy-check-steps/{step_id}",
        json={
            "failure_behavior": "record_only",
            "min_confidence": None,
            "metadata": {"review_ticket": "GOV-123"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["failure_behavior"] == "record_only"
    assert body["min_confidence"] is None
    assert body["metadata"] == {"review_ticket": "GOV-123"}


def test_policy_check_step_patch_can_move_to_another_rule(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    other_rule_id = create_policy_rule(client, policy_id=policy_id, name="Other rule")
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(
        f"/policy-check-steps/{step_id}",
        json={"policy_rule_id": other_rule_id},
    )

    assert response.status_code == 200
    assert response.json()["policy_rule_id"] == other_rule_id


def test_empty_policy_check_step_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(f"/policy-check-steps/{step_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_policy_check_step_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/policy-check-steps/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyCheckStep not found."


def test_policy_check_step_create_unknown_rule_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_rule_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=missing_rule_id),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyRule not found."


def test_policy_check_step_update_unknown_rule_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]
    missing_rule_id = "00000000-0000-0000-0000-000000000001"

    response = client.patch(
        f"/policy-check-steps/{step_id}",
        json={"policy_rule_id": missing_rule_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyRule not found."


def test_policy_check_steps_for_unknown_rule_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_rule_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/policy-rules/{missing_rule_id}/check-steps")

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyRule not found."


def test_policy_check_step_create_unknown_check_tool_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    missing_check_tool_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(
            policy_rule_id=rule_id,
            check_tool_id=missing_check_tool_id,
        ),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "CheckTool not found."


def test_policy_check_step_rejects_mismatched_check_tool_type(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    check_tool_id = create_check_tool(
        session_factory,
        name="source_status_checker",
        tool_type=CheckToolType.SOURCE_STATUS_CHECK,
    )

    response = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(
            policy_rule_id=rule_id,
            check_tool_id=check_tool_id,
        ),
    )

    assert response.status_code == 422
    assert "does not match" in response.json()["detail"]


def test_policy_check_step_update_rejects_mismatched_check_tool_type(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    check_tool_id = create_check_tool(
        session_factory,
        name="source_status_checker",
        tool_type=CheckToolType.SOURCE_STATUS_CHECK,
    )
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(
        f"/policy-check-steps/{step_id}",
        json={"check_tool_id": check_tool_id},
    )

    assert response.status_code == 422
    assert "does not match" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {"check_type": "source_status", "target_selector": "model_id"},
        {"min_confidence": 1.1},
        {"metadata": {"raw_prompt_ref": "do-not-store"}},
        {"policy_rule_id": None},
        {"check_type": None},
        {"target_selector": None},
        {"required": None},
        {"failure_behavior": None},
        {"status": None},
        {"evidence_retention": None},
        {"metadata": None},
    ],
)
def test_policy_check_step_update_rejects_invalid_payloads(
    api_client: tuple[TestClient, SessionFactory],
    payload: dict[str, object],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(f"/policy-check-steps/{step_id}", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"check_type": "source_status", "target_selector": "model_id"},
        {"min_confidence": -0.1},
        {"metadata": {"scanner_payload": "do-not-store"}},
        {"tool_name": "external_scanner"},
    ],
)
def test_policy_check_step_create_rejects_invalid_payloads(
    api_client: tuple[TestClient, SessionFactory],
    payload: dict[str, object],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)

    response = client.post(
        "/policy-check-steps",
        json={**policy_check_step_payload(policy_rule_id=rule_id), **payload},
    )

    assert response.status_code == 422


def test_audit_log_created_on_policy_check_step_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)

    response = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )

    assert response.status_code == 201
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_check_step_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "policy_check_step"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {
        "operation": "create",
        "policy_rule_id": rule_id,
        "check_type": "data_usage_profile_status",
        "target_selector": "source_ids",
    }
    assert "runtime_metadata_pre_check" not in str(audit_log.metadata_)


def test_audit_log_created_on_policy_check_step_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(
        f"/policy-check-steps/{step_id}",
        json={"failure_behavior": "record_only"},
    )

    assert response.status_code == 200
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_check_step_updated"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "policy_check_step"
    assert audit_log.entity_id == step_id
    assert audit_log.metadata_ == {"updated_fields": "failure_behavior"}


def test_audit_log_created_on_policy_check_step_status_change(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)
    created = client.post(
        "/policy-check-steps",
        json=policy_check_step_payload(policy_rule_id=rule_id),
    )
    step_id = created.json()["id"]

    response = client.patch(
        f"/policy-check-steps/{step_id}",
        json={"status": "disabled"},
    )

    assert response.status_code == 200
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_check_step_status_changed"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "policy_check_step"
    assert audit_log.entity_id == step_id
    assert audit_log.metadata_ == {
        "updated_fields": "status",
        "status_from": "active",
        "status_to": "disabled",
    }


def test_policy_check_step_audit_metadata_does_not_include_raw_keys_or_payloads(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    rule_id = create_policy_rule(client, policy_id=policy_id)

    response = client.post(
        "/policy-check-steps",
        json={
            **policy_check_step_payload(policy_rule_id=rule_id),
            "metadata": {"review_ticket": "GOV-123"},
        },
    )

    assert response.status_code == 201
    audit_blob = str([log.metadata_ for log in fetch_audit_logs(session_factory)])
    assert "api_key" not in audit_blob
    assert "raw_payload" not in audit_blob
    assert "review_ticket" not in audit_blob


def create_policy(client: TestClient, *, name: str = "Email policy") -> str:
    response = client.post(
        "/policies",
        json={
            "name": name,
            "description": "Governed email policy.",
            "status": "draft",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_policy_rule(
    client: TestClient,
    *,
    policy_id: str,
    name: str = "Email review rule",
) -> str:
    response = client.post(
        "/policy-rules",
        json={
            "policy_id": policy_id,
            "name": name,
            "description": "Require review before governed email tool use.",
            "condition": (
                '{"decision":"require_human_review",'
                '"reason":"Email tool use requires human review.",'
                '"tool_name":"send_email"}'
            ),
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def create_check_tool(
    session_factory: SessionFactory,
    *,
    name: str = "data_usage_profile_checker",
    tool_type: CheckToolType = CheckToolType.DATA_USAGE_PROFILE_CHECK,
) -> str:
    with session_factory() as session:
        check_tool = CheckTool(
            name=name,
            description="Checks declared Source usage metadata.",
            tool_type=tool_type,
            status=CheckToolStatus.ACTIVE,
            owner_type=OwnerType.TEAM,
            owner_id="team:governance",
            owner_name="Governance",
            metadata_={"source": "internal_metadata"},
        )
        session.add(check_tool)
        session.commit()
        return str(check_tool.id)


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def policy_check_step_payload(
    *,
    policy_rule_id: str,
    check_tool_id: str | None = None,
) -> dict[str, object]:
    return {
        "policy_rule_id": policy_rule_id,
        "check_tool_id": check_tool_id,
        "check_type": "data_usage_profile_status",
        "target_selector": "source_ids",
        "required": True,
        "failure_behavior": "require_human_review",
        "min_confidence": 0.8,
        "status": "active",
        "evidence_retention": "evidence_bundle",
        "metadata": {"purpose": "runtime_metadata_pre_check"},
    }
