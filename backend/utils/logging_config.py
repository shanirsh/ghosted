"""Structured logging configuration for Ghosted Cloud AI."""

import logging
import sys
from typing import Optional
import structlog
from structlog.stdlib import LoggerFactory
import uuid

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
logging.captureWarnings(True)


def get_request_id() -> str:
    return str(uuid.uuid4())


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


def bind_request_context(
    logger, request_id: Optional[str] = None, user_id: Optional[str] = None
) -> structlog.BoundLogger:
    context = {"request_id": request_id or get_request_id()}
    if user_id:
        context["user_id"] = user_id
    return logger.bind(**context)


def configure_logging():
    return get_logger("ghosted-cloud-ai")
