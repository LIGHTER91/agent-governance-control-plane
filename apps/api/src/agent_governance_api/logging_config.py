import logging

from agent_governance_api.metadata_safety import redact_sensitive_text


class SensitiveDataLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive_text(record.getMessage())
        record.args = ()
        return True


def configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _install_sensitive_data_filter(logging.getLogger())


def _install_sensitive_data_filter(logger: logging.Logger) -> None:
    if not any(isinstance(item, SensitiveDataLogFilter) for item in logger.filters):
        logger.addFilter(SensitiveDataLogFilter())

    for handler in logger.handlers:
        if not any(
            isinstance(item, SensitiveDataLogFilter) for item in handler.filters
        ):
            handler.addFilter(SensitiveDataLogFilter())
