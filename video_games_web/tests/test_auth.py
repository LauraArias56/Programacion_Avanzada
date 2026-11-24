"""Pruebas de registro, login y logout."""

from app.extensions import db
from app.models import AuditLog, User
from tests.helpers import login, logout, register


def test_register_creates_user_and_audit(app, client):
    response = register(client)

    assert response.status_code == 200
    assert b"Cuenta creada correctamente" in response.data

    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == "tester@example.com")
        )
        assert user is not None
        assert user.is_admin is False

        audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "auth.register")
        )
        assert audit is not None
        assert audit.user_id == user.id
        assert audit.status == "success"


def test_register_rejects_duplicate_email(app, client):
    register(client)
    logout(client)

    response = register(client, username="otro")

    assert b"Ya existe una cuenta con este email" in response.data

    with app.app_context():
        count = db.session.scalar(
            db.select(db.func.count()).select_from(User)
        )
        assert count == 1


def test_login_success_and_failure_are_audited(app, client):
    register(client)
    logout(client)

    failed = login(client, password="incorrecta")
    assert "Email o contraseña incorrectos".encode() in failed.data

    success = login(client)
    assert b"Sesion iniciada" in success.data

    with app.app_context():
        actions = db.session.scalars(db.select(AuditLog.action)).all()
        assert "auth.login_failed" in actions
        assert "auth.login_success" in actions

        failed_audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "auth.login_failed")
        )
        assert failed_audit.status == "failure"
        assert failed_audit.meta["email"] == "tester@example.com"


def test_logout_requires_post_and_is_audited(app, client):
    register(client)
    response = logout(client)

    assert response.status_code == 200
    assert b"Sesion cerrada" in response.data

    with app.app_context():
        audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "auth.logout")
        )
        assert audit is not None
