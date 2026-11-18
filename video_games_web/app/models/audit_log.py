"""Modelo de auditoria de acciones de usuario."""

from datetime import datetime, timezone

from ..extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = db.Column(db.String(80), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="success")
    request_id = db.Column(db.String(64), nullable=True, index=True)
    ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    meta = db.Column("metadata", db.JSON, nullable=False, default=dict)
    error = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.status}>"
