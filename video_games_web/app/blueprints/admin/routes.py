"""Visor de auditoria para administradores."""

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ...extensions import db
from ...models import AuditLog, User
from ...services.audit import record_audit

bp = Blueprint("admin", __name__, url_prefix="/admin")
logger = logging.getLogger("app.admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@bp.route("/audit")
@login_required
@admin_required
def audit():
    page = request.args.get("page", 1, type=int)
    action = request.args.get("action", "").strip()
    user_query = request.args.get("user", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()

    stmt = (
        db.select(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_query:
        like = f"%{user_query}%"
        stmt = stmt.where(
            AuditLog.user.has(
                or_(User.email.ilike(like), User.username.ilike(like))
            )
        )
    start = _parse_date(date_from)
    if start:
        stmt = stmt.where(AuditLog.created_at >= start)
    end = _parse_date(date_to)
    if end:
        stmt = stmt.where(AuditLog.created_at < end + timedelta(days=1))

    pagination = db.paginate(
        stmt,
        page=max(page, 1),
        per_page=current_app.config["AUDIT_PAGE_SIZE"],
        error_out=False,
    )
    actions = db.session.scalars(
        db.select(AuditLog.action).distinct().order_by(AuditLog.action)
    ).all()

    record_audit(
        "admin.audit_viewed",
        metadata={"page": page, "action": action or None},
    )
    db.session.commit()

    return render_template(
        "admin/audit.html",
        pagination=pagination,
        entries=pagination.items,
        actions=actions,
        filters={
            "action": action,
            "user": user_query,
            "from": date_from,
            "to": date_to,
        },
    )
