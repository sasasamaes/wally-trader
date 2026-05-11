"""Structured logging with automatic secret redaction.

We use structlog so logs are JSON in production and pretty-printed in dev.
The `redact_secrets_processor` scrubs anything that looks like an API key
(sk-…, gsk_…, AIza…, ya29…, etc.) before serialization. This is a defense-
in-depth layer — the real protection is never logging the raw secret in
the first place.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import get_settings

_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),      # Anthropic
    re.compile(r"sk-[A-Za-z0-9]{20,}"),              # OpenAI / generic
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),             # Groq
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),          # Google
    re.compile(r"ya29\.[A-Za-z0-9_\-]{20,}"),        # Google OAuth
    re.compile(r"xoxb-[A-Za-z0-9\-]{20,}"),          # Slack
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),             # GitHub
    re.compile(r"whsec_[A-Za-z0-9]{20,}"),           # Stripe webhook
]


def _redact_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED-KEY]", redacted)
    return redacted


def redact_secrets_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    for key, value in list(event_dict.items()):
        event_dict[key] = _redact_value(value)
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        redact_secrets_processor,
    ]

    if settings.is_production:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Tame noisy libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


log = structlog.get_logger()
