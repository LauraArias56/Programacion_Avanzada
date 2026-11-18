"""Hooks de peticion: request_id, contexto de usuario y logs de acceso."""

import logging
from time import perf_counter
from uuid import uuid4

from flask import g, request
from flask_login import current_user

from .logging_config import request_id_var, user_id_var

request_logger = logging.getLogger("app.request")


def _current_user_id() -> int | None:
    try:
        if current_user.is_authenticated:
            return current_user.id
    except Exception:  # pragma: no cover - contexto incompleto
        return None
    return None


def register_hooks(app) -> None:
    @app.before_request
    def start_request():
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        g.request_id = request_id
        g.request_start = perf_counter()
        user_id = _current_user_id()
        g.request_user_id = user_id
        request_id_var.set(request_id)
        user_id_var.set(user_id)

    @app.after_request
    def log_request(response):
        if request.endpoint == "static":
            return response

        duration = (
            perf_counter() - getattr(g, "request_start", perf_counter())
        ) * 1000
        user_id_var.set(_current_user_id() or getattr(g, "request_user_id", None))
        request_logger.info(
            "http_request",
            extra={
                "http_method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration, 2),
                "ip": request.remote_addr,
            },
        )
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response

    @app.teardown_request
    def reset_context(exc=None):
        if exc is not None:
            request_logger.exception("unhandled_exception", exc_info=exc)
        request_id_var.set(None)
        user_id_var.set(None)
