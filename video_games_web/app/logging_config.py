"""Logging estructurado (JSON) con request_id, rotacion y redaccion.

Los logs se escriben a stdout (para `docker compose logs`) y a archivos
rotativos en LOG_DIR: app.log y error.log.
"""

import json
import logging
import logging.config
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)

_SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|authorization|cookie|token|secret)\b"
    r"(\s*[:=]\s*)(?:(?:bearer|basic)\s+)?(\S+)"
)

_EXTRA_FIELDS = (
    "request_id",
    "user_id",
    "http_method",
    "path",
    "status",
    "duration_ms",
    "ip",
    "attempt",
    "action",
    "audit_status",
    "audit_user_id",
    "model_version",
    "prediction_id",
    "error",
)


def redact(text: str) -> str:
    """Reemplaza valores sensibles por *** en un texto."""
    return _SENSITIVE_PATTERN.sub(r"\1\2***", text)


class SensitiveDataFilter(logging.Filter):
    """Evita que contrasenas, tokens o cookies lleguen a los logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        key: redact(value) if isinstance(value, str) else value
                        for key, value in record.args.items()
                    }
                else:
                    record.args = tuple(
                        redact(value) if isinstance(value, str) else value
                        for value in record.args
                    )
        except Exception:  # pragma: no cover - nunca debe romper el logging
            pass
        return True


class RequestContextFilter(logging.Filter):
    """Inyecta request_id y user_id en cada registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Formatea cada registro como una linea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None and value != "-":
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _build_config(app) -> dict:
    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)

    level = app.config["LOG_LEVEL"]
    max_bytes = app.config["LOG_MAX_BYTES"]
    backup_count = app.config["LOG_BACKUP_COUNT"]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {"()": "app.logging_config.RequestContextFilter"},
            "sensitive": {"()": "app.logging_config.SensitiveDataFilter"},
        },
        "formatters": {
            "json": {"()": "app.logging_config.JsonFormatter"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
                "filters": ["request_context", "sensitive"],
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_dir / "app.log"),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
                "delay": True,
                "formatter": "json",
                "filters": ["request_context", "sensitive"],
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_dir / "error.log"),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
                "delay": True,
                "level": "ERROR",
                "formatter": "json",
                "filters": ["request_context", "sensitive"],
            },
        },
        "root": {
            "level": level,
            "handlers": ["console", "file", "error_file"],
        },
        "loggers": {
            "app": {"level": level, "handlers": [], "propagate": True},
            "werkzeug": {"level": level, "handlers": [], "propagate": True},
            "httpx": {"level": "WARNING", "handlers": [], "propagate": True},
        },
    }


def configure_logging(app) -> None:
    logging.config.dictConfig(_build_config(app))
    # Asegura que el logger de la app no conserve handlers propios de Flask.
    app.logger.handlers.clear()
    app.logger.propagate = True
    app.logger.setLevel(app.config["LOG_LEVEL"])
