"""Pruebas del visor de auditoria."""

from app.extensions import db
from app.models import User
from tests.helpers import register


def test_admin_page_forbidden_for_regular_users(client):
    register(client)

    response = client.get("/admin/audit")

    assert response.status_code == 403


def test_admin_can_view_audit_log(app, client):
    register(client)
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == "tester@example.com")
        )
        user.is_admin = True
        db.session.commit()

    response = client.get("/admin/audit")

    assert response.status_code == 200
    assert b"auth.register" in response.data
    assert b"tester@example.com" in response.data


def test_admin_audit_view_is_itself_audited(app, client):
    register(client)
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == "tester@example.com")
        )
        user.is_admin = True
        db.session.commit()

    client.get("/admin/audit")

    with app.app_context():
        from app.models import AuditLog

        audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "admin.audit_viewed")
        )
        assert audit is not None
