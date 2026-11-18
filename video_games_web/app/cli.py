"""Comandos de linea de comandos de la aplicacion."""

from datetime import datetime, timedelta, timezone

import click
from flask.cli import with_appcontext
from sqlalchemy import delete

from .extensions import db
from .models import AuditLog, User
from .services.audit import record_audit


def register_cli(app) -> None:
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--username", prompt=True)
    @click.option(
        "--password", prompt=True, hide_input=True, confirmation_prompt=True
    )
    @with_appcontext
    def create_admin(email: str, username: str, password: str):
        """Crea un usuario administrador."""
        email = User.normalize_email(email)
        username = username.strip()
        if db.session.scalar(db.select(User).where(User.email == email)):
            raise click.ClickException("Ya existe un usuario con ese email.")
        if db.session.scalar(db.select(User).where(User.username == username)):
            raise click.ClickException("Ya existe un usuario con ese nombre.")
        user = User(email=email, username=username, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        record_audit("admin.created", user=user, metadata={"email": email})
        db.session.commit()
        click.echo(f"Administrador creado: {email}")

    @app.cli.command("audit-prune")
    @click.option("--days", default=90, show_default=True, type=int)
    @with_appcontext
    def audit_prune(days: int):
        """Elimina registros de auditoria mas antiguos que N dias."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = db.session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        db.session.commit()
        click.echo(f"Registros eliminados: {result.rowcount}")
