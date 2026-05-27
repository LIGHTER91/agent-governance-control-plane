import pytest

from agent_governance_api.metadata_safety import (
    REDACTED_VALUE,
    filter_safe_metadata,
    is_unsafe_metadata_key,
    redact_sensitive_text,
    reject_unsafe_metadata_keys,
    unsafe_metadata_keys,
)


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "access_token",
        "refresh_token",
        "password",
        "client_secret",
        "authorization",
        "raw_content",
        "source_content",
        "chunks",
        "prompt",
        "raw_prompt",
        "raw_payload",
        "private_customer_data",
    ],
)
def test_rejects_centralized_unsafe_metadata_keys(key: str) -> None:
    with pytest.raises(ValueError, match="Metadata contains unsafe key names."):
        reject_unsafe_metadata_keys({key: "do-not-store"})


def test_detects_nested_unsafe_metadata_keys() -> None:
    metadata = {"safe": "kept", "nested": {"authorization": "Bearer secret"}}

    assert unsafe_metadata_keys(metadata) == ["nested.authorization"]
    with pytest.raises(ValueError, match="Metadata contains unsafe key names."):
        reject_unsafe_metadata_keys(metadata)


def test_filter_safe_metadata_drops_unsafe_and_non_primitive_values() -> None:
    metadata = {
        "safe": "kept",
        "count": 1,
        "enabled": True,
        "api_key": "do-not-export",
        "nested": {"safe": "not-exported"},
        "items": ["not-exported"],
    }

    assert filter_safe_metadata(metadata) == {
        "safe": "kept",
        "count": 1,
        "enabled": True,
    }


def test_is_unsafe_metadata_key_matches_substrings_case_insensitively() -> None:
    assert is_unsafe_metadata_key("ClientSecret")
    assert is_unsafe_metadata_key("x_authorization_header")
    assert not is_unsafe_metadata_key("tool_name")


def test_redact_sensitive_text_redacts_known_key_assignments() -> None:
    message = (
        "api_key=abc123 token=tok123 authorization: Bearer secret, tool_name=send_email"
    )

    redacted = redact_sensitive_text(message)

    assert "abc123" not in redacted
    assert "tok123" not in redacted
    assert "Bearer secret" not in redacted
    assert f"api_key={REDACTED_VALUE}" in redacted
    assert f"token={REDACTED_VALUE}" in redacted
    assert f"authorization: {REDACTED_VALUE}" in redacted
    assert "tool_name=send_email" in redacted
