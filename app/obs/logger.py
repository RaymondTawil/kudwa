from __future__ import annotations
import json, logging, sys, time, uuid
from typing import Any, Dict
from fastapi import Request

# List of keys used in the JSON log format
JSON_FMT_KEYS = [
    "ts", "level", "event", "request_id", "method", "path", "status", "duration_ms", "extra"
]


class JsonFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs logs in JSON format for structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),  # Timestamp
            "level": record.levelname.lower(),  # Log level (info, error, etc.)
            "event": record.getMessage(),       # Log message
        }
        # Attach extra fields from the log record, excluding standard attributes
        for k, v in getattr(record, "__dict__", {}).items():
            if k in ("args", "msg", "levelno", "levelname", "pathname", "filename", "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process", "name"):
                continue
            payload[k] = v
        return json.dumps(payload, ensure_ascii=False)


# Configure the main logger for the application
logger = logging.getLogger("finance_ai")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False  # Prevent duplicate logs


async def logging_middleware(request: Request, call_next):
    """
    FastAPI middleware for logging HTTP requests and responses in JSON format.
    Adds a unique request ID and logs request details and duration.
    """
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())  # Unique request ID
    start = time.perf_counter()
    try:
        resp = await call_next(request)
        status = resp.status_code
    except Exception as e:
        status = 500
        logger.exception("request_error", extra={
            "request_id": rid, "method": request.method, "path": request.url.path, "error": str(e)
        })
        raise
    finally:
        dur = (time.perf_counter() - start) * 1000.0  # Duration in ms
        logger.info("request_done", extra={
            "request_id": rid,
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "duration_ms": round(dur, 2),
        })
    resp.headers["x-request-id"] = rid  # Add request ID to response headers
    return resp