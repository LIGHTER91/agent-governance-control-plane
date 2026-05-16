import re
from collections.abc import Mapping

SafeMetadataValue = str | int | float | bool | None
SafeMetadata = dict[str, SafeMetadataValue]

UNSAFE_METADATA_KEY_PARTS = (
    "access_token",
    "api_key",
    "authorization",
    "credential",
    "password",
    "payload",
    "private_customer_data",
    "raw_payload",
    "raw_prompt",
    "refresh_token",
    "secret",
    "token",
)

REDACTED_VALUE = "[REDACTED]"

_SENSITIVE_KEY_PATTERN = (
    r"[A-Za-z0-9_.-]*(?:"
    + "|".join(re.escape(part) for part in UNSAFE_METADATA_KEY_PARTS)
    + r")[A-Za-z0-9_.-]*"
)
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    rf"\b({_SENSITIVE_KEY_PATTERN})(\s*[:=]\s*)(.*?)(?="
    rf"(?:\s+{_SENSITIVE_KEY_PATTERN}\s*[:=])|[,}}\]\n]|$)",
    re.IGNORECASE,
)


def reject_unsafe_metadata_keys(
    metadata: Mapping[str, object],
    *,
    error_message: str = "Metadata contains unsafe key names.",
) -> SafeMetadata:
    if unsafe_metadata_keys(metadata):
        raise ValueError(error_message)
    return dict(metadata)


def unsafe_metadata_keys(metadata: Mapping[str, object]) -> list[str]:
    return _unsafe_metadata_keys(metadata)


def is_unsafe_metadata_key(key: str) -> bool:
    normalized_key = key.lower()
    return any(part in normalized_key for part in UNSAFE_METADATA_KEY_PARTS)


def filter_safe_metadata(metadata: Mapping[str, object] | None) -> SafeMetadata:
    safe_metadata: SafeMetadata = {}
    for key, value in dict(metadata or {}).items():
        if not isinstance(key, str) or is_unsafe_metadata_key(key):
            continue
        if _is_safe_metadata_value(value):
            safe_metadata[key] = value
    return safe_metadata


def redact_sensitive_text(text: str) -> str:
    return _SENSITIVE_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_VALUE}",
        text,
    )


def _unsafe_metadata_keys(
    metadata: Mapping[str, object],
    *,
    prefix: str = "",
) -> list[str]:
    unsafe_keys: list[str] = []
    for key, value in metadata.items():
        key_text = str(key)
        key_path = f"{prefix}.{key_text}" if prefix else key_text
        if is_unsafe_metadata_key(key_text):
            unsafe_keys.append(key_path)
        if isinstance(value, Mapping):
            unsafe_keys.extend(_unsafe_metadata_keys(value, prefix=key_path))
    return unsafe_keys


def _is_safe_metadata_value(value: object) -> bool:
    return isinstance(value, str | int | float | bool) or value is None
