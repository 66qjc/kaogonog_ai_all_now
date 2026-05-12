"""Structured logging utilities for backend services."""
from __future__ import annotations

import contextvars
from datetime import datetime, timezone
import json
import logging
import logging.config
from pathlib import Path
import re
from typing import Any
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send


request_id_var = contextvars.ContextVar("request_id", default="")
user_id_var = contextvars.ContextVar("user_id", default="")
method_var = contextvars.ContextVar("method", default="")
path_var = contextvars.ContextVar("path", default="")

SENSITIVE_KEYWORDS = (
    "authorization",
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "api-v3-key",
    "private_key",
    "pay_sign",
    "paysign",
    "signature",
    "ciphertext",
    "openid",
    "open_id",
    "session_key",
    "access_token",
    "refresh_token",
)

SENSITIVE_PATTERNS = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"([?&](?:token|access_token|secret|password|key)=)[^&\s]+", re.IGNORECASE),
    re.compile(r"((?:api[_-]?key|secret|password|token)\s*[:=]\s*)[^\s,;}]+", re.IGNORECASE),
)

STANDARD_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key or "").lower().replace("-", "_")
    return any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)


def redact(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        sanitized = value
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r"\1***", sanitized)
        if len(sanitized) > 1200:
            return f"{sanitized[:1200]}..."
        return sanitized
    if isinstance(value, dict):
        return {
            str(key): "***" if _is_sensitive_key(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    return redact(str(value))


def set_log_context(**values: str) -> None:
    if "request_id" in values:
        request_id_var.set(str(values["request_id"] or ""))
    if "user_id" in values:
        user_id_var.set(str(values["user_id"] or ""))
    if "method" in values:
        method_var.set(str(values["method"] or ""))
    if "path" in values:
        path_var.set(str(values["path"] or ""))


def get_log_context() -> dict:
    return {
        "request_id": request_id_var.get(),
        "user_id": user_id_var.get(),
        "method": method_var.get(),
        "path": path_var.get(),
    }


def _record_extra(record: logging.LogRecord) -> dict:
    extra = {}
    for key, value in record.__dict__.items():
        if key in STANDARD_RECORD_ATTRS or key.startswith("_"):
            continue
        extra[key] = value
    return extra


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = get_log_context()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": context["request_id"],
            "user_id": context["user_id"],
            "method": context["method"],
            "path": context["path"],
        }
        payload.update(redact(_record_extra(record)))
        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "",
                "message": redact(str(record.exc_info[1] or "")),
                "stack": redact(self.formatException(record.exc_info)),
            }
        if record.stack_info:
            payload["stack_info"] = redact(self.formatStack(record.stack_info))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class TextLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = get_log_context()
        record.request_id = context["request_id"] or "-"
        record.user_id = context["user_id"] or "-"
        record.method = context["method"] or "-"
        record.path = context["path"] or "-"
        record.msg = redact(record.msg)
        if isinstance(record.args, dict):
            record.args = redact(record.args)
        elif record.args:
            record.args = tuple(redact(item) for item in record.args)
        return super().format(record)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg)
        if isinstance(record.args, dict):
            record.args = redact(record.args)
        elif record.args:
            record.args = tuple(redact(item) for item in record.args)
        return True


def configure_logging(settings) -> None:
    log_level = str(getattr(settings, "log_level", "INFO") or "INFO").upper()
    log_format = str(getattr(settings, "log_format", "json") or "json").lower()
    formatter_name = "json" if log_format == "json" else "text"

    handlers: dict[str, dict] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": formatter_name,
            "filters": ["redaction"],
        }
    }

    log_file = str(getattr(settings, "log_file", "") or "").strip()
    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = Path(getattr(settings, "backend_root", Path.cwd())) / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": formatter_name,
            "filters": ["redaction"],
            "filename": str(log_path),
            "maxBytes": int(getattr(settings, "log_max_bytes", 10485760) or 10485760),
            "backupCount": int(getattr(settings, "log_backup_count", 10) or 10),
            "encoding": "utf-8",
        }

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "redaction": {
                "()": RedactionFilter,
            }
        },
        "formatters": {
            "json": {
                "()": JsonLogFormatter,
            },
            "text": {
                "()": TextLogFormatter,
                "format": "%(asctime)s [%(levelname)s] request_id=%(request_id)s user_id=%(user_id)s %(name)s: %(message)s",
            },
        },
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            "uvicorn": {"level": log_level, "propagate": True},
            "uvicorn.error": {"level": log_level, "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": True},
        },
    })


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> str:
    target = name.lower()
    for key, value in headers:
        if key.lower() == target:
            return value.decode("latin1")
    return ""


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp, access_log_enabled: bool = True) -> None:
        self.app = app
        self.access_log_enabled = access_log_enabled
        self.logger = logging.getLogger("app.access")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        headers = list(scope.get("headers") or [])
        request_id = _header_value(headers, b"x-request-id") or uuid.uuid4().hex
        method = str(scope.get("method") or "")
        path = str(scope.get("path") or "")
        client = scope.get("client") or ("", 0)
        client_ip = client[0] if client else ""
        status_code = 500
        started_at = time.perf_counter()
        request_token = request_id_var.set(request_id)
        method_token = method_var.set(method)
        path_token = path_var.set(path)
        user_token = user_id_var.set("")

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status") or status_code)
                response_headers = list(message.get("headers") or [])
                response_headers.append((b"x-request-id", request_id.encode("latin1")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "HTTP request failed",
                extra={
                    "event": "http.request.exception",
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )
            raise
        finally:
            if self.access_log_enabled:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                self.logger.info(
                    "HTTP request completed",
                    extra={
                        "event": "http.request.completed",
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                    },
                )
            request_id_var.reset(request_token)
            user_id_var.reset(user_token)
            method_var.reset(method_token)
            path_var.reset(path_token)
