import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


def bind_log_context(**fields: Any) -> dict[str, Any]:
    # used for attaching run-wide fields (run_id, source, partition) to every later record
    current = dict(_log_context.get())
    current.update(fields)
    _log_context.set(current)
    return current


def current_log_context() -> dict[str, Any]:
    # used for passing the run's identity across a process boundary, where a contextvar cannot follow
    return dict(_log_context.get())


def clear_log_context() -> None:
    # used for dropping the bound fields when a run ends
    _log_context.set({})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # used for turning a log record plus the bound context into one json line
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(_log_context.get())
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    # used for installing the json formatter once, at process start
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("scrapy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    # used for giving every module a logger without importing logging everywhere
    return logging.getLogger(name)
