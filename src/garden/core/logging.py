import json
import logging
import sys
import time
from functools import wraps
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for machine-readable output."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        return json.dumps(log_data)


def setup_logging(verbose: bool = False, structured: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING

    if structured:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(StructuredFormatter())
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(name)s %(levelname)s: %(message)s"))

    logger = logging.getLogger("garden")
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"garden.{name}")


def timed(operation: str | None = None):
    """Decorator that logs execution time of a function."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"garden.perf")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                op_name = operation or func.__qualname__
                logger.debug(
                    "%s completed in %.1fms",
                    op_name,
                    elapsed,
                    extra={"duration_ms": round(elapsed, 1), "operation": op_name},
                )
                return result
            except Exception:
                elapsed = (time.perf_counter() - start) * 1000
                op_name = operation or func.__qualname__
                logger.debug(
                    "%s failed after %.1fms",
                    op_name,
                    elapsed,
                    extra={"duration_ms": round(elapsed, 1), "operation": op_name},
                )
                raise

        return wrapper

    return decorator
