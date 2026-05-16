import logging

from agent_governance_api.logging_config import SensitiveDataLogFilter
from agent_governance_api.metadata_safety import REDACTED_VALUE


def test_sensitive_data_log_filter_redacts_sensitive_assignments() -> None:
    record = logging.LogRecord(
        name="agent_governance_api.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request metadata api_key=%s authorization: Bearer secret",
        args=("abc123",),
        exc_info=None,
    )

    assert SensitiveDataLogFilter().filter(record) is True

    message = record.getMessage()
    assert "abc123" not in message
    assert "Bearer secret" not in message
    assert f"api_key={REDACTED_VALUE}" in message
    assert f"authorization: {REDACTED_VALUE}" in message


def test_sensitive_data_log_filter_preserves_non_sensitive_message() -> None:
    record = logging.LogRecord(
        name="agent_governance_api.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="tool_name=send_email event_type=tool_call_requested",
        args=(),
        exc_info=None,
    )

    SensitiveDataLogFilter().filter(record)

    assert record.getMessage() == "tool_name=send_email event_type=tool_call_requested"
