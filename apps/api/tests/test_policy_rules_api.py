import json
from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
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


def test_create_policy_rule(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    policy_id = create_policy(client)

    response = client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, name="Email review rule"),
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["policy_id"] == policy_id
    assert body["name"] == "Email review rule"
    assert body["description"] == "Require review before governed email tool use."
    assert json.loads(body["condition"]) == {
        "decision": "require_human_review",
        "reason": "Email tool use requires human review.",
        "tool_name": "send_email",
    }
    assert body["created_at"]
    assert body["updated_at"]


def test_create_policy_rule_accepts_contextual_condition_fields(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    capability_id = uuid4()
    source_id = uuid4()
    model_id = uuid4()

    response = client.post(
        "/policy-rules",
        json=policy_rule_payload(
            policy_id=policy_id,
            name="Contextual vectorization deny rule",
            condition=json.dumps(
                {
                    "decision": "deny",
                    "reason": "Declared confidential vectorization is denied.",
                    "tool_name": "vectorize_source",
                    "action_type": "vectorize",
                    "capability_id": str(capability_id),
                    "source_ids": [str(source_id)],
                    "model_id": str(model_id),
                    "purpose": "semantic_search_indexing",
                    "data_classification": "confidential",
                    "contains_personal_data": True,
                    "contains_sensitive_data": False,
                }
            ),
        ),
    )

    assert response.status_code == 201
    assert json.loads(response.json()["condition"]) == {
        "decision": "deny",
        "reason": "Declared confidential vectorization is denied.",
        "tool_name": "vectorize_source",
        "action_type": "vectorize",
        "capability_id": str(capability_id),
        "source_ids": [str(source_id)],
        "model_id": str(model_id),
        "purpose": "semantic_search_indexing",
        "data_classification": "confidential",
        "contains_personal_data": True,
        "contains_sensitive_data": False,
    }


def test_list_policy_rules(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, name="Email review rule"),
    )
    client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, name="Payment deny rule"),
    )

    response = client.get("/policy-rules")

    assert response.status_code == 200
    assert {rule["name"] for rule in response.json()} == {
        "Email review rule",
        "Payment deny rule",
    }


def test_list_policy_rules_for_policy(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client, name="Email policy")
    other_policy_id = create_policy(client, name="Payment policy")
    client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, name="Email review rule"),
    )
    client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=other_policy_id, name="Payment deny rule"),
    )

    response = client.get(f"/policies/{policy_id}/rules")

    assert response.status_code == 200
    body = response.json()
    assert [rule["name"] for rule in body] == ["Email review rule"]
    assert {rule["policy_id"] for rule in body} == {policy_id}


def test_get_policy_rule_by_id(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    created = client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, name="Email review rule"),
    )
    rule_id = created.json()["id"]

    response = client.get(f"/policy-rules/{rule_id}")

    assert response.status_code == 200
    assert response.json()["id"] == rule_id
    assert response.json()["name"] == "Email review rule"


def test_update_policy_rule(api_client: tuple[TestClient, SessionFactory]) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]

    response = client.patch(
        f"/policy-rules/{rule_id}",
        json={
            "name": "Production email review rule",
            "description": None,
            "condition": condition_json(environment="production"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Production email review rule"
    assert body["description"] is None
    assert json.loads(body["condition"])["environment"] == "production"


def test_update_policy_rule_policy_id(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client, name="Email policy")
    other_policy_id = create_policy(client, name="Production policy")
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]

    response = client.patch(
        f"/policy-rules/{rule_id}",
        json={"policy_id": other_policy_id},
    )

    assert response.status_code == 200
    assert response.json()["policy_id"] == other_policy_id


def test_empty_policy_rule_update_is_rejected(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]

    response = client.patch(f"/policy-rules/{rule_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No update fields provided."


def test_policy_rule_not_found_behavior(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/policy-rules/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "PolicyRule not found."


def test_list_policy_rules_for_unknown_policy_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_policy_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(f"/policies/{missing_policy_id}/rules")

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy not found."


def test_create_policy_rule_unknown_policy_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    missing_policy_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=missing_policy_id),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy not found."


def test_update_policy_rule_unknown_policy_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]
    missing_policy_id = "00000000-0000-0000-0000-000000000001"

    response = client.patch(
        f"/policy-rules/{rule_id}",
        json={"policy_id": missing_policy_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy not found."


@pytest.mark.parametrize("name", ["", "   "])
def test_policy_rule_create_rejects_blank_name(
    api_client: tuple[TestClient, SessionFactory],
    name: str,
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)

    response = client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, name=name),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("condition", ["", "   "])
def test_policy_rule_create_rejects_blank_condition(
    api_client: tuple[TestClient, SessionFactory],
    condition: str,
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)

    response = client.post(
        "/policy-rules",
        json=policy_rule_payload(policy_id=policy_id, condition=condition),
    )

    assert response.status_code == 422


def test_policy_rule_create_rejects_unsupported_condition_fields(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)

    response = client.post(
        "/policy-rules",
        json=policy_rule_payload(
            policy_id=policy_id,
            condition=json.dumps(
                {
                    "decision": "deny",
                    "reason": "Model matching is not supported.",
                    "model_name": "gpt-example",
                }
            ),
        ),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [{"policy_id": None}, {"name": None}, {"condition": None}],
)
def test_policy_rule_update_rejects_null_required_fields(
    api_client: tuple[TestClient, SessionFactory],
    payload: dict[str, object],
) -> None:
    client, _ = api_client
    policy_id = create_policy(client)
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]

    response = client.patch(f"/policy-rules/{rule_id}", json=payload)

    assert response.status_code == 422


def test_audit_log_created_on_policy_rule_create(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)

    response = create_policy_rule(client, policy_id=policy_id)

    assert response.status_code == 201
    audit_log = fetch_audit_logs(session_factory)[-1]
    assert audit_log.event_type == "policy_rule_created"
    assert audit_log.actor_type is ActorType.DEVELOPMENT
    assert audit_log.actor_id == "dev-placeholder"
    assert audit_log.entity_type == "policy_rule"
    assert audit_log.entity_id == response.json()["id"]
    assert audit_log.metadata_ == {"operation": "create", "policy_id": policy_id}
    assert "condition" not in str(audit_log.metadata_)


def test_audit_log_created_on_policy_rule_update(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client)
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]

    response = client.patch(
        f"/policy-rules/{rule_id}",
        json={"condition": condition_json(environment="production")},
    )

    assert response.status_code == 200
    update_log = fetch_audit_logs(session_factory)[-1]
    assert update_log.event_type == "policy_rule_updated"
    assert update_log.actor_type is ActorType.DEVELOPMENT
    assert update_log.actor_id == "dev-placeholder"
    assert update_log.entity_type == "policy_rule"
    assert update_log.entity_id == rule_id
    assert update_log.metadata_ == {"updated_fields": "condition"}
    assert "send_email" not in str(update_log.metadata_)


def test_audit_log_records_policy_rule_policy_move(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    policy_id = create_policy(client, name="Email policy")
    other_policy_id = create_policy(client, name="Production policy")
    created = create_policy_rule(client, policy_id=policy_id)
    rule_id = created.json()["id"]

    response = client.patch(
        f"/policy-rules/{rule_id}",
        json={"policy_id": other_policy_id},
    )

    assert response.status_code == 200
    update_log = fetch_audit_logs(session_factory)[-1]
    assert update_log.event_type == "policy_rule_updated"
    assert update_log.metadata_ == {
        "updated_fields": "policy_id",
        "policy_id_from": policy_id,
        "policy_id_to": other_policy_id,
    }


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


def create_policy_rule(client: TestClient, *, policy_id: str) -> Response:
    return client.post("/policy-rules", json=policy_rule_payload(policy_id=policy_id))


def fetch_audit_logs(session_factory: SessionFactory) -> list[AuditLog]:
    with session_factory() as session:
        statement = select(AuditLog).order_by(AuditLog.created_at, AuditLog.id)
        return list(session.scalars(statement).all())


def policy_rule_payload(
    *,
    policy_id: str,
    name: str = "Email review rule",
    condition: str | None = None,
) -> dict[str, object]:
    return {
        "policy_id": policy_id,
        "name": name,
        "description": "Require review before governed email tool use.",
        "condition": condition if condition is not None else condition_json(),
    }


def condition_json(*, environment: str | None = None) -> str:
    condition = {
        "decision": "require_human_review",
        "reason": "Email tool use requires human review.",
        "tool_name": "send_email",
    }
    if environment is not None:
        condition["environment"] = environment
    return json.dumps(condition)
