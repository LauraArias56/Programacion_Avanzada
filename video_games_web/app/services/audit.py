"""Registro de eventos de auditoria en PostgreSQL."""

import logging

from flask import g, has_request_context, request
from flask_login import current_user

from ..extensions import db
from ..models import AuditLog

audit_logger = logging.getLogger("app.audit")


def record_audit(
    action: str,
    status: str = "success",
    user=None,
    metadata: dict | None = None,
    error: str | None = None,
) -> AuditLog:
    """Anade un registro de auditoria a la sesion actual (sin hacer commit)."""
    if user is None and has_request_context():
        try:
            if current_user.is_authenticated:
                user = current_user._get_current_object()
        except Exception:  # pragma: no cover - contexto incompleto
            user = None

    user_id = getattr(user, "id", None)
    request_id = getattr(g, "request_id", None) if has_request_context() else None
    ip = request.remote_addr if has_request_context() else None
    user_agent = None
    if has_request_context():
        user_agent = (request.user_agent.string or "")[:255] or None

    entry = AuditLog(
        user_id=user_id,
        action=action,
        status=status,
        request_id=request_id,
        ip=ip,
        user_agent=user_agent,
        meta=metadata or {},
        error=error,
    )
    db.session.add(entry)
    audit_logger.info(
        "audit_event",
        extra={
            "action": action,
            "audit_status": status,
            "audit_user_id": user_id,
        },
    )
    return entry
