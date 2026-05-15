from collections.abc import Mapping

SafeMetadataValue = str | int | float | bool | None
SafeMetadata = dict[str, SafeMetadataValue]

UNSAFE_METADATA_KEY_PARTS = (
    "api_key",
    "authorization",
    "credential",
    "password",
    "raw_payload",
    "raw_prompt",
    "secret",
    "token",
)


def reject_unsafe_metadata_keys(
    metadata: Mapping[str, SafeMetadataValue],
) -> SafeMetadata:
    unsafe_keys = [
        key
        for key in metadata
        if any(part in key.lower() for part in UNSAFE_METADATA_KEY_PARTS)
    ]
    if unsafe_keys:
        raise ValueError("Metadata contains unsafe key names.")
    return dict(metadata)
