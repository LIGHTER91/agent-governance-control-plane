from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from agent_governance_api.auth import ActorContext, get_current_actor
from agent_governance_api.database import Base, get_db_session
from agent_governance_api.main import app
from agent_governance_api.models import (
    AccessGrant,
    AccessGrantStatus,
    AccessGrantSubjectType,
    AccessGrantTargetType,
    AccessGrantType,
    ActorType,
    AgentRunRecord,
    AuditLog,
    Capability,
    CapabilityStatus,
    CapabilityType,
    DataSource,
    DataSourceStatus,
    DataSourceType,
    Environment,
    HumanApproval,
    HumanApprovalStatus,
    ModelAsset,
    ModelAssetStatus,
    ModelAssetType,
    ModelProvider,
    OwnerType,
    Policy,
    PolicyDecision,
    PolicyDecisionValue,
    PolicyRule,
    PolicyStatus,
    RiskLevel,
    TraceEventRecord,
    TraceEventType,
)

SessionFactory = Callable[[], Session]


@pytest.fixture()
def api_client() -> Iterator[tuple[TestClient, SessionFactory]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
    app.dependency_overrides[get_current_actor] = lambda: auditor_actor()
    try:
        with TestClient(app) as client:
            yield client, testing_session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_successful_evidence_bundle_export(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["id"] == str(agent_id)
    assert body["agent"]["owner_id"] == "team:ai-platform"
    assert set(body) == {
        "agent",
        "audit_logs",
        "agent_runs",
        "trace_events",
        "policy_decisions",
        "human_approvals",
        "access_grants",
        "capability_references",
        "source_references",
        "model_asset_references",
    }
    assert body["access_grants"] == []
    assert body["capability_references"] == []
    assert body["source_references"] == []
    assert body["model_asset_references"] == []


def test_successful_evidence_bundle_export_creates_safe_audit_log(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [audit_log] = fetch_evidence_bundle_export_audit_logs(session_factory)
    assert audit_log.event_type == "evidence_bundle_exported"
    assert audit_log.actor_type is ActorType.USER
    assert audit_log.actor_id == "user:auditor-1"
    assert audit_log.entity_type == "agent"
    assert audit_log.entity_id == str(agent_id)
    assert audit_log.summary == "Evidence Bundle exported."
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "export_format": "json",
        "audit_log_count": 2,
        "agent_run_count": 1,
        "trace_event_count": 1,
        "policy_decision_count": 1,
        "human_approval_count": 1,
        "access_grant_count": 0,
        "capability_reference_count": 0,
        "source_reference_count": 0,
        "model_asset_reference_count": 0,
    }
    assert "agent_runs" not in audit_log.metadata_
    assert "trace_events" not in audit_log.metadata_
    assert "policy_decisions" not in audit_log.metadata_
    assert "human_approvals" not in audit_log.metadata_
    assert "access_grants" not in audit_log.metadata_
    assert "capability_references" not in audit_log.metadata_
    assert "source_references" not in audit_log.metadata_
    assert "model_asset_references" not in audit_log.metadata_
    assert fetch_evidence_bundle_export_denied_audit_logs(session_factory) == []


def test_evidence_bundle_includes_agent_access_grants_and_inventory_references(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    other_agent_id = create_agent(
        client,
        agent_payload(name="Other support assistant"),
    )
    seeded = seed_access_inventory_records(
        session_factory,
        agent_id=agent_id,
        other_agent_id=other_agent_id,
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    access_grants = body["access_grants"]
    assert {grant["name"] for grant in access_grants} == {
        "Capability access",
        "Source access",
        "Model access",
    }
    assert "Other agent access" not in {grant["name"] for grant in access_grants}
    assert {grant["subject_id"] for grant in access_grants} == {str(agent_id)}
    target_ids_by_type = {
        grant["target_type"]: grant["target_id"] for grant in access_grants
    }
    assert target_ids_by_type == {
        "capability": str(seeded.capability_id),
        "source": str(seeded.source_id),
        "model_asset": str(seeded.model_asset_id),
    }

    [capability] = body["capability_references"]
    assert capability["id"] == str(seeded.capability_id)
    assert capability["name"] == "Send support email"
    assert capability["capability_type"] == "tool"
    assert capability["external_ref"] == "tool:send_email"
    assert capability["status"] == "active"
    assert capability["risk_level"] == "medium"
    assert capability["metadata"] == {"domain": "support"}

    [source] = body["source_references"]
    assert source["id"] == str(seeded.source_id)
    assert source["name"] == "Support knowledge base"
    assert source["source_type"] == "knowledge_base"
    assert source["external_ref"] == "kb:support"
    assert source["owner_type"] == "team"
    assert source["owner_id"] == "team:support-ops"
    assert source["status"] == "active"
    assert source["risk_level"] == "medium"
    assert source["metadata"] == {"system": "runbook_index"}

    [model_asset] = body["model_asset_references"]
    assert model_asset["id"] == str(seeded.model_asset_id)
    assert model_asset["name"] == "Support chat model"
    assert model_asset["model_type"] == "llm"
    assert model_asset["provider"] == "openai"
    assert model_asset["model_ref"] == "gpt-4.1-mini"
    assert model_asset["version"] == "2026-01"
    assert model_asset["owner_type"] == "team"
    assert model_asset["owner_id"] == "team:ai-platform"
    assert model_asset["status"] == "active"
    assert model_asset["risk_level"] == "medium"
    assert model_asset["metadata"] == {"usage": "assistant_response"}


def test_evidence_bundle_filters_access_inventory_metadata(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    other_agent_id = create_agent(
        client,
        agent_payload(name="Other support assistant"),
    )
    seeded = seed_access_inventory_records(
        session_factory,
        agent_id=agent_id,
        other_agent_id=other_agent_id,
    )
    inject_unsafe_access_inventory_metadata(session_factory, seeded)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    [grant] = [
        grant for grant in body["access_grants"] if grant["target_type"] == "capability"
    ]
    [capability] = body["capability_references"]
    [source] = body["source_references"]
    [model_asset] = body["model_asset_references"]
    assert grant["metadata"] == {"review_status": "approved"}
    assert capability["metadata"] == {"domain": "support"}
    assert source["metadata"] == {"system": "runbook_index"}
    assert model_asset["metadata"] == {"usage": "assistant_response"}
    assert "do-not-export" not in response.text
    assert "api_key" not in response.text
    assert "authorization" not in response.text
    assert "raw_payload" not in response.text
    assert "secret" not in response.text


def test_successful_evidence_bundle_export_audit_counts_access_inventory(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    other_agent_id = create_agent(
        client,
        agent_payload(name="Other support assistant"),
    )
    seed_evidence_records(session_factory, agent_id)
    seed_access_inventory_records(
        session_factory,
        agent_id=agent_id,
        other_agent_id=other_agent_id,
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [audit_log] = fetch_evidence_bundle_export_audit_logs(session_factory)
    assert audit_log.metadata_["access_grant_count"] == 3
    assert audit_log.metadata_["capability_reference_count"] == 1
    assert audit_log.metadata_["source_reference_count"] == 1
    assert audit_log.metadata_["model_asset_reference_count"] == 1
    assert "access_grants" not in audit_log.metadata_
    assert "capability_references" not in audit_log.metadata_
    assert "source_references" not in audit_log.metadata_
    assert "model_asset_references" not in audit_log.metadata_


def test_denied_evidence_bundle_export_creates_safe_audit_log(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Evidence Bundle export is not permitted for this actor."
    }
    assert_denied_response_has_no_bundle_sections(response.json())
    assert fetch_evidence_bundle_export_audit_logs(session_factory) == []
    [audit_log] = fetch_evidence_bundle_export_denied_audit_logs(session_factory)
    assert audit_log.event_type == "evidence_bundle_export_denied"
    assert audit_log.actor_type is ActorType.USER
    assert audit_log.actor_id == "user:viewer-1"
    assert audit_log.entity_type == "agent"
    assert audit_log.entity_id == str(agent_id)
    assert audit_log.summary == "Evidence Bundle export denied."
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "reason": "forbidden",
        "export_format": "json",
    }
    assert "audit_logs" not in audit_log.metadata_
    assert "agent_runs" not in audit_log.metadata_
    assert "trace_events" not in audit_log.metadata_
    assert "policy_decisions" not in audit_log.metadata_
    assert "human_approvals" not in audit_log.metadata_
    assert "send_email" not in str(audit_log.metadata_)


def test_platform_admin_can_export_evidence_bundle(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:platform-admin",
            roles=("platform_admin",),
        )
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    assert response.json()["agent"]["id"] == str(agent_id)


def test_direct_user_owner_can_export_evidence_bundle(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    owner_id = "user:evidence-owner-1"
    agent_id = create_agent(
        client,
        agent_payload(
            owner_type="user",
            owner_id=owner_id,
            owner_name="Evidence Owner",
        ),
    )
    seed_evidence_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id=owner_id,
            roles=(),
        )
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["id"] == str(agent_id)
    assert body["agent"]["owner_type"] == "user"
    assert body["agent"]["owner_id"] == owner_id
    [audit_log] = fetch_evidence_bundle_export_audit_logs(session_factory)
    assert audit_log.event_type == "evidence_bundle_exported"
    assert audit_log.actor_type is ActorType.USER
    assert audit_log.actor_id == owner_id
    assert audit_log.entity_type == "agent"
    assert audit_log.entity_id == str(agent_id)
    assert audit_log.metadata_["agent_id"] == str(agent_id)
    assert audit_log.metadata_["export_format"] == "json"
    assert fetch_evidence_bundle_export_denied_audit_logs(session_factory) == []


def test_non_owner_user_is_denied_evidence_bundle_export(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(
        client,
        agent_payload(
            owner_type="user",
            owner_id="user:evidence-owner-1",
            owner_name="Evidence Owner",
        ),
    )
    seed_evidence_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:not-the-owner",
            roles=(),
        )
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Evidence Bundle export is not permitted for this actor."
    }
    assert_denied_response_has_no_bundle_sections(response.json())
    assert fetch_evidence_bundle_export_audit_logs(session_factory) == []
    [audit_log] = fetch_evidence_bundle_export_denied_audit_logs(session_factory)
    assert audit_log.event_type == "evidence_bundle_export_denied"
    assert audit_log.actor_type is ActorType.USER
    assert audit_log.actor_id == "user:not-the-owner"
    assert audit_log.entity_type == "agent"
    assert audit_log.entity_id == str(agent_id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "reason": "forbidden",
        "export_format": "json",
    }


@pytest.mark.parametrize(
    "actor",
    [
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        ),
        ActorContext(
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            roles=(),
        ),
    ],
)
def test_actor_without_auditor_or_platform_admin_gets_403(
    api_client: tuple[TestClient, SessionFactory],
    actor: ActorContext,
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)
    set_current_actor(actor)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Evidence Bundle export is not permitted for this actor."
    }
    assert_denied_response_has_no_bundle_sections(response.json())
    assert fetch_evidence_bundle_export_audit_logs(session_factory) == []
    [audit_log] = fetch_evidence_bundle_export_denied_audit_logs(session_factory)
    assert audit_log.event_type == "evidence_bundle_export_denied"
    assert audit_log.entity_id == str(agent_id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "reason": "forbidden",
        "export_format": "json",
    }


def test_service_actor_gets_403_by_default(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)
    set_current_actor(
        ActorContext(
            actor_type=ActorType.SERVICE,
            actor_id="service:runtime-adapter",
            roles=("runtime:decision", "runtime:resume", "telemetry:write"),
        )
    )

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Evidence Bundle export is not permitted for this actor."
    }
    assert_denied_response_has_no_bundle_sections(response.json())
    assert fetch_evidence_bundle_export_audit_logs(session_factory) == []
    [audit_log] = fetch_evidence_bundle_export_denied_audit_logs(session_factory)
    assert audit_log.event_type == "evidence_bundle_export_denied"
    assert audit_log.actor_type is ActorType.SERVICE
    assert audit_log.actor_id == "service:runtime-adapter"
    assert audit_log.entity_id == str(agent_id)
    assert audit_log.metadata_ == {
        "agent_id": str(agent_id),
        "reason": "forbidden",
        "export_format": "json",
    }


def test_evidence_bundle_unknown_agent_returns_404(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    missing_agent_id = uuid4()

    response = client.get(f"/agents/{missing_agent_id}/evidence-bundle")

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found."
    assert fetch_evidence_bundle_export_audit_logs(session_factory) == []
    assert fetch_evidence_bundle_export_denied_audit_logs(session_factory) == []


def test_denied_evidence_bundle_unknown_agent_returns_403_without_audit_log(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    missing_agent_id = uuid4()
    set_current_actor(
        ActorContext(
            actor_type=ActorType.USER,
            actor_id="user:viewer-1",
            roles=("viewer",),
        )
    )

    response = client.get(f"/agents/{missing_agent_id}/evidence-bundle")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Evidence Bundle export is not permitted for this actor."
    }
    assert str(missing_agent_id) not in response.text
    assert_denied_response_has_no_bundle_sections(response.json())
    assert fetch_evidence_bundle_export_audit_logs(session_factory) == []
    assert fetch_evidence_bundle_export_denied_audit_logs(session_factory) == []


def test_evidence_bundle_includes_audit_logs(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    audit_logs = response.json()["audit_logs"]
    assert [log["event_type"] for log in audit_logs] == [
        "agent_created",
        "agent_updated",
    ]
    assert audit_logs[0]["entity_id"] == str(agent_id)
    assert audit_logs[1]["metadata"] == {"updated_fields": "risk_level"}


def test_evidence_bundle_includes_trace_events(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    [agent_run] = body["agent_runs"]
    [trace_event] = body["trace_events"]
    assert agent_run["run_id"] == str(seeded.run_id)
    assert agent_run["metadata"] == {"source": "api-test"}
    assert trace_event["id"] == str(seeded.trace_event_id)
    assert trace_event["external_event_id"] == "vendor-event-123"
    assert trace_event["metadata"] == {"tool_name": "send_email"}


def test_evidence_bundle_includes_policy_decisions_with_references(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [decision] = response.json()["policy_decisions"]
    assert decision["id"] == str(seeded.policy_decision_id)
    assert decision["decision"] == "deny"
    assert decision["policy_id"] == str(seeded.policy_id)
    assert decision["rule_id"] == str(seeded.rule_id)
    assert decision["policy"] == {
        "id": str(seeded.policy_id),
        "name": "Tool access policy",
        "status": "active",
    }
    assert decision["rule"] == {
        "id": str(seeded.rule_id),
        "policy_id": str(seeded.policy_id),
        "name": "Deny email tool",
    }


def test_evidence_bundle_represents_policy_decisions_linked_to_trace_events(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [decision] = response.json()["policy_decisions"]
    assert decision["trace_event_id"] == str(seeded.trace_event_id)


def test_evidence_bundle_includes_human_approvals(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [approval] = response.json()["human_approvals"]
    assert approval["id"] == str(seeded.human_approval_id)
    assert approval["agent_id"] == str(agent_id)
    assert approval["status"] == "approved"
    assert approval["requested_by_actor_type"] == "development"
    assert approval["requested_by_actor_id"] == "dev-placeholder"
    assert approval["reviewed_by_actor_type"] == "development"
    assert approval["reviewed_by_actor_id"] == "dev-placeholder"
    assert approval["reason"] == "High-risk action requires review."
    assert approval["decision_note"] == "Approved for evidence test."
    assert approval["created_at"]
    assert approval["reviewed_at"]
    assert approval["expires_at"] is None


def test_evidence_bundle_represents_approvals_linked_to_policy_decisions(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    [approval] = response.json()["human_approvals"]
    assert approval["policy_decision_id"] == str(seeded.policy_decision_id)


def test_evidence_bundle_represents_automated_review_approval_chain(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    create_review_policy_rule(session_factory)
    run_id = uuid4()
    event_id = uuid4()

    ingest_response = client.post(
        "/telemetry/events",
        json=trace_event_payload(
            agent_id,
            event_id=event_id,
            run_id=run_id,
        ),
    )
    bundle_response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert ingest_response.status_code == 201
    ingest_body = ingest_response.json()
    assert ingest_body["policy_decision"]["decision"] == "require_human_review"
    assert ingest_body["human_approval_id"] is not None
    assert bundle_response.status_code == 200

    body = bundle_response.json()
    [trace_event] = body["trace_events"]
    [policy_decision] = body["policy_decisions"]
    [human_approval] = body["human_approvals"]
    human_approval_audit_logs = [
        audit_log
        for audit_log in body["audit_logs"]
        if audit_log["event_type"] == "human_approval_requested"
    ]
    [human_approval_audit_log] = human_approval_audit_logs

    assert trace_event["id"] == str(event_id)
    assert trace_event["agent_id"] == str(agent_id)
    assert trace_event["run_id"] == str(run_id)
    assert trace_event["event_type"] == "tool_call_requested"
    assert trace_event["metadata"] == {"tool_name": "send_email"}

    assert policy_decision["id"] == ingest_body["policy_decision"]["id"]
    assert policy_decision["agent_id"] == str(agent_id)
    assert policy_decision["trace_event_id"] == trace_event["id"]
    assert policy_decision["decision"] == "require_human_review"
    assert policy_decision["policy"]
    assert policy_decision["rule"]

    assert human_approval["id"] == ingest_body["human_approval_id"]
    assert human_approval["agent_id"] == str(agent_id)
    assert human_approval["policy_decision_id"] == policy_decision["id"]
    assert human_approval["status"] == "pending"
    assert human_approval["requested_by_actor_type"] == "development"
    assert human_approval["requested_by_actor_id"] == "dev-placeholder"

    assert human_approval_audit_log["entity_type"] == "human_approval"
    assert human_approval_audit_log["entity_id"] == human_approval["id"]
    assert human_approval_audit_log["metadata"] == {
        "agent_id": str(agent_id),
        "status": "pending",
        "policy_decision_id": policy_decision["id"],
    }


def test_evidence_bundle_filters_unsafe_metadata_fields(
    api_client: tuple[TestClient, SessionFactory],
) -> None:
    client, session_factory = api_client
    agent_id = create_agent(client)
    seeded = seed_evidence_records(session_factory, agent_id)
    inject_unsafe_metadata(session_factory, agent_id, seeded)

    response = client.get(f"/agents/{agent_id}/evidence-bundle")

    assert response.status_code == 200
    body = response.json()
    unsafe_audit_log = body["audit_logs"][-1]
    [agent_run] = body["agent_runs"]
    [trace_event] = body["trace_events"]
    assert unsafe_audit_log["metadata"] == {"safe_note": "kept"}
    assert agent_run["metadata"] == {"source": "api-test"}
    assert trace_event["metadata"] == {"tool_name": "send_email"}
    assert "api_key" not in str(body)
    assert "token" not in str(body)
    assert "raw_payload" not in str(body)
    assert "private_customer_data" not in str(body)


class SeededEvidence:
    def __init__(
        self,
        *,
        run_id: UUID,
        trace_event_id: UUID,
        policy_id: UUID,
        rule_id: UUID,
        policy_decision_id: UUID,
        human_approval_id: UUID,
    ) -> None:
        self.run_id = run_id
        self.trace_event_id = trace_event_id
        self.policy_id = policy_id
        self.rule_id = rule_id
        self.policy_decision_id = policy_decision_id
        self.human_approval_id = human_approval_id


class SeededAccessInventory:
    def __init__(
        self,
        *,
        capability_id: UUID,
        source_id: UUID,
        model_asset_id: UUID,
        capability_grant_id: UUID,
        source_grant_id: UUID,
        model_grant_id: UUID,
        other_agent_grant_id: UUID,
    ) -> None:
        self.capability_id = capability_id
        self.source_id = source_id
        self.model_asset_id = model_asset_id
        self.capability_grant_id = capability_grant_id
        self.source_grant_id = source_grant_id
        self.model_grant_id = model_grant_id
        self.other_agent_grant_id = other_agent_grant_id


def create_agent(
    client: TestClient,
    payload: dict[str, object] | None = None,
) -> UUID:
    response = client.post("/agents", json=payload or agent_payload())

    assert response.status_code == 201
    return UUID(response.json()["id"])


def auditor_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.USER,
        actor_id="user:auditor-1",
        roles=("auditor",),
    )


def set_current_actor(actor: ActorContext) -> None:
    app.dependency_overrides[get_current_actor] = lambda: actor


def assert_denied_response_has_no_bundle_sections(body: dict[str, object]) -> None:
    assert not {
        "agent",
        "audit_logs",
        "agent_runs",
        "trace_events",
        "policy_decisions",
        "human_approvals",
        "access_grants",
        "capability_references",
        "source_references",
        "model_asset_references",
    } & set(body)


def fetch_evidence_bundle_export_audit_logs(
    session_factory: SessionFactory,
) -> list[AuditLog]:
    return fetch_evidence_bundle_audit_logs(
        session_factory,
        event_type="evidence_bundle_exported",
    )


def fetch_evidence_bundle_export_denied_audit_logs(
    session_factory: SessionFactory,
) -> list[AuditLog]:
    return fetch_evidence_bundle_audit_logs(
        session_factory,
        event_type="evidence_bundle_export_denied",
    )


def fetch_evidence_bundle_audit_logs(
    session_factory: SessionFactory,
    *,
    event_type: str,
) -> list[AuditLog]:
    with session_factory() as session:
        return list(
            session.scalars(
                select(AuditLog).where(AuditLog.event_type == event_type)
            ).all()
        )


def seed_evidence_records(
    session_factory: SessionFactory,
    agent_id: UUID,
) -> SeededEvidence:
    with session_factory() as session:
        created_at = datetime.now(UTC)
        audit_log = AuditLog(
            event_type="agent_updated",
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            entity_type="agent",
            entity_id=str(agent_id),
            summary="Agent risk level updated.",
            metadata_={"updated_fields": "risk_level"},
            created_at=created_at,
        )
        run_id = uuid4()
        run = AgentRunRecord(
            agent_id=agent_id,
            run_id=run_id,
            correlation_id="corr-123",
            environment=Environment.DEVELOPMENT,
            status="observed",
            started_at=created_at,
            summary="Agent run observed.",
            metadata_={"source": "api-test"},
            created_at=created_at,
        )
        trace_event = TraceEventRecord(
            agent_id=agent_id,
            run_id=run_id,
            external_event_id="vendor-event-123",
            correlation_id="corr-123",
            event_type=TraceEventType.TOOL_CALL_REQUESTED,
            timestamp=created_at,
            summary="Tool call requested.",
            metadata_={"tool_name": "send_email"},
            created_at=created_at,
        )
        policy = Policy(
            name="Tool access policy",
            description=None,
            status=PolicyStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add_all([audit_log, run, trace_event, policy])
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Deny email tool",
            description=None,
            condition='{"decision":"deny","reason":"Email is denied."}',
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(rule)
        session.flush()

        decision = PolicyDecision(
            agent_id=agent_id,
            policy_id=policy.id,
            rule_id=rule.id,
            trace_event_id=trace_event.id,
            decision=PolicyDecisionValue.DENY,
            reason="Email is denied.",
            context_hash="sha256:evidence-test",
            created_at=created_at,
        )
        session.add(decision)
        session.flush()

        approval = HumanApproval(
            agent_id=agent_id,
            policy_decision_id=decision.id,
            status=HumanApprovalStatus.APPROVED,
            requested_by_actor_type=ActorType.DEVELOPMENT,
            requested_by_actor_id="dev-placeholder",
            reviewed_by_actor_type=ActorType.DEVELOPMENT,
            reviewed_by_actor_id="dev-placeholder",
            reason="High-risk action requires review.",
            decision_note="Approved for evidence test.",
            created_at=created_at,
            reviewed_at=created_at,
            expires_at=None,
        )
        session.add(approval)
        session.commit()
        return SeededEvidence(
            run_id=run_id,
            trace_event_id=trace_event.id,
            policy_id=policy.id,
            rule_id=rule.id,
            policy_decision_id=decision.id,
            human_approval_id=approval.id,
        )


def seed_access_inventory_records(
    session_factory: SessionFactory,
    *,
    agent_id: UUID,
    other_agent_id: UUID,
) -> SeededAccessInventory:
    with session_factory() as session:
        created_at = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        capability = Capability(
            name="Send support email",
            description="Send approved support email responses.",
            capability_type=CapabilityType.TOOL,
            external_ref="tool:send_email",
            status=CapabilityStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"domain": "support"},
            created_at=created_at,
            updated_at=created_at,
        )
        source = DataSource(
            name="Support knowledge base",
            description="Curated support runbook articles.",
            source_type=DataSourceType.KNOWLEDGE_BASE,
            external_ref="kb:support",
            owner_type=OwnerType.TEAM,
            owner_id="team:support-ops",
            owner_name="Support Operations",
            owner_contact_email="support-ops@example.com",
            status=DataSourceStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"system": "runbook_index"},
            created_at=created_at + timedelta(seconds=1),
            updated_at=created_at + timedelta(seconds=1),
        )
        model_asset = ModelAsset(
            name="Support chat model",
            description="Hosted LLM for support response drafting.",
            model_type=ModelAssetType.LLM,
            provider=ModelProvider.OPENAI,
            model_ref="gpt-4.1-mini",
            version="2026-01",
            owner_type=OwnerType.TEAM,
            owner_id="team:ai-platform",
            owner_name="AI Platform",
            owner_contact_email="ai-platform@example.com",
            status=ModelAssetStatus.ACTIVE,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"usage": "assistant_response"},
            created_at=created_at + timedelta(seconds=2),
            updated_at=created_at + timedelta(seconds=2),
        )
        session.add_all([capability, source, model_asset])
        session.flush()

        capability_grant = AccessGrant(
            name="Capability access",
            description="Allows use of the support email capability.",
            grant_type=AccessGrantType.CAPABILITY,
            subject_type=AccessGrantSubjectType.AGENT,
            subject_id=agent_id,
            target_type=AccessGrantTargetType.CAPABILITY,
            target_id=capability.id,
            external_ref=None,
            status=AccessGrantStatus.ACTIVE,
            granted_by_actor_type=ActorType.DEVELOPMENT,
            granted_by_actor_id="dev-placeholder",
            reason="Governance review completed.",
            expires_at=None,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"review_status": "approved"},
            created_at=created_at + timedelta(seconds=3),
            updated_at=created_at + timedelta(seconds=3),
        )
        source_grant = AccessGrant(
            name="Source access",
            description="Allows access to support knowledge articles.",
            grant_type=AccessGrantType.SOURCE,
            subject_type=AccessGrantSubjectType.AGENT,
            subject_id=agent_id,
            target_type=AccessGrantTargetType.SOURCE,
            target_id=source.id,
            external_ref=None,
            status=AccessGrantStatus.ACTIVE,
            granted_by_actor_type=ActorType.DEVELOPMENT,
            granted_by_actor_id="dev-placeholder",
            reason="Governance review completed.",
            expires_at=None,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"review_status": "approved"},
            created_at=created_at + timedelta(seconds=4),
            updated_at=created_at + timedelta(seconds=4),
        )
        model_grant = AccessGrant(
            name="Model access",
            description="Allows use of the support chat model.",
            grant_type=AccessGrantType.MODEL,
            subject_type=AccessGrantSubjectType.AGENT,
            subject_id=agent_id,
            target_type=AccessGrantTargetType.MODEL_ASSET,
            target_id=model_asset.id,
            external_ref=None,
            status=AccessGrantStatus.ACTIVE,
            granted_by_actor_type=ActorType.DEVELOPMENT,
            granted_by_actor_id="dev-placeholder",
            reason="Governance review completed.",
            expires_at=None,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"review_status": "approved"},
            created_at=created_at + timedelta(seconds=5),
            updated_at=created_at + timedelta(seconds=5),
        )
        other_agent_grant = AccessGrant(
            name="Other agent access",
            description="Belongs to a different Agent.",
            grant_type=AccessGrantType.CAPABILITY,
            subject_type=AccessGrantSubjectType.AGENT,
            subject_id=other_agent_id,
            target_type=AccessGrantTargetType.CAPABILITY,
            target_id=capability.id,
            external_ref=None,
            status=AccessGrantStatus.ACTIVE,
            granted_by_actor_type=ActorType.DEVELOPMENT,
            granted_by_actor_id="dev-placeholder",
            reason="Governance review completed.",
            expires_at=None,
            risk_level=RiskLevel.MEDIUM,
            metadata_={"review_status": "approved"},
            created_at=created_at + timedelta(seconds=6),
            updated_at=created_at + timedelta(seconds=6),
        )
        session.add_all(
            [
                capability_grant,
                source_grant,
                model_grant,
                other_agent_grant,
            ]
        )
        session.commit()
        return SeededAccessInventory(
            capability_id=capability.id,
            source_id=source.id,
            model_asset_id=model_asset.id,
            capability_grant_id=capability_grant.id,
            source_grant_id=source_grant.id,
            model_grant_id=model_grant.id,
            other_agent_grant_id=other_agent_grant.id,
        )


def create_review_policy_rule(session_factory: SessionFactory) -> tuple[UUID, UUID]:
    with session_factory() as session:
        created_at = datetime.now(UTC)
        policy = Policy(
            name="Human review policy",
            description=None,
            status=PolicyStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(policy)
        session.flush()

        rule = PolicyRule(
            policy_id=policy.id,
            name="Require review for email tool",
            description=None,
            condition=(
                '{"decision":"require_human_review",'
                '"reason":"Email tool requires human review.",'
                '"tool_name":"send_email"}'
            ),
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(rule)
        session.commit()
        return policy.id, rule.id


def inject_unsafe_metadata(
    session_factory: SessionFactory,
    agent_id: UUID,
    seeded: SeededEvidence,
) -> None:
    with session_factory() as session:
        unsafe_audit_log = AuditLog(
            event_type="agent_reviewed",
            actor_type=ActorType.DEVELOPMENT,
            actor_id="dev-placeholder",
            entity_type="agent",
            entity_id=str(agent_id),
            summary="Agent reviewed.",
            metadata_={
                "safe_note": "kept",
                "api_key": "do-not-export",
                "password": "do-not-export",
                "private_customer_data": "do-not-export",
            },
            created_at=datetime.now(UTC),
        )
        session.add(unsafe_audit_log)
        session.execute(
            AgentRunRecord.__table__.update()
            .where(AgentRunRecord.run_id == seeded.run_id)
            .values(
                {
                    "metadata": {
                        "source": "api-test",
                        "raw_payload": "do-not-export",
                    }
                }
            )
        )
        session.execute(
            TraceEventRecord.__table__.update()
            .where(TraceEventRecord.id == seeded.trace_event_id)
            .values(
                {
                    "metadata": {
                        "tool_name": "send_email",
                        "token": "do-not-export",
                        "authorization": "Bearer do-not-export",
                        "nested": {"secret": "do-not-export"},
                    }
                }
            )
        )
        session.commit()


def inject_unsafe_access_inventory_metadata(
    session_factory: SessionFactory,
    seeded: SeededAccessInventory,
) -> None:
    with session_factory() as session:
        session.execute(
            AccessGrant.__table__.update()
            .where(AccessGrant.id == seeded.capability_grant_id)
            .values(
                {
                    "metadata": {
                        "review_status": "approved",
                        "api_key": "do-not-export",
                    }
                }
            )
        )
        session.execute(
            Capability.__table__.update()
            .where(Capability.id == seeded.capability_id)
            .values(
                {
                    "metadata": {
                        "domain": "support",
                        "authorization": "Bearer do-not-export",
                    }
                }
            )
        )
        session.execute(
            DataSource.__table__.update()
            .where(DataSource.id == seeded.source_id)
            .values(
                {
                    "metadata": {
                        "system": "runbook_index",
                        "raw_payload": "do-not-export",
                    }
                }
            )
        )
        session.execute(
            ModelAsset.__table__.update()
            .where(ModelAsset.id == seeded.model_asset_id)
            .values(
                {
                    "metadata": {
                        "usage": "assistant_response",
                        "secret": "do-not-export",
                    }
                }
            )
        )
        session.commit()


def agent_payload(**overrides: object) -> dict[str, object]:
    payload = {
        "name": "Support assistant",
        "description": "Routes support requests.",
        "owner_type": "team",
        "owner_id": "team:ai-platform",
        "owner_name": "AI Platform",
        "owner_contact_email": "owner@example.com",
        "environment": "development",
        "status": "draft",
        "risk_level": "low",
        "framework": "LangGraph",
    }
    payload.update(overrides)
    return payload


def trace_event_payload(
    agent_id: UUID,
    *,
    event_id: UUID,
    run_id: UUID,
) -> dict[str, object]:
    return {
        "id": str(event_id),
        "agent_id": str(agent_id),
        "run_id": str(run_id),
        "correlation_id": "corr-123",
        "event_type": "tool_call_requested",
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": "Tool call requested.",
        "metadata": {"tool_name": "send_email"},
    }
