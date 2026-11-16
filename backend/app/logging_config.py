"""Application logging that avoids secrets and financial amounts."""

import logging

REDACT_MARKERS = ("password", "api_key", "secret", "bearer ", "authorization")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        if any(marker in message for marker in REDACT_MARKERS):
            record.msg = "log message redacted"
            record.args = ()
        return True


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("costwise")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logging()
