"""
Structured logging configuration shared by the FastAPI app and the Lambda
functions. Logs are emitted as single-line JSON so they can be ingested
directly by CloudWatch Logs / any log aggregator.

IMPORTANT: never log passwords, JWT secrets, AWS credentials, or full
request bodies that might contain sensitive data.
"""
import json
import logging
import sys
import time
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Allow callers to pass structured extras via `extra={"data": {...}}`
        if hasattr(record, "data"):
            payload["data"] = record.data
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. re-imported in Lambda warm start)
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
