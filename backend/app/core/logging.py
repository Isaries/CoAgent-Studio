import logging
import sys

import structlog
from structlog.types import Processor


def setup_logging(json_logs: bool = False, log_level: str = "INFO") -> None:
    """
    Configure structlog and standard logging.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        # JSON logs for production (Splunk, ELK, Datadog)
        processors = [
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty console logs for local development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    # Intercept Uvicorn logs
    for _u in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        _logger = logging.getLogger(_u)
        _logger.handlers = []
        _logger.propagate = True
