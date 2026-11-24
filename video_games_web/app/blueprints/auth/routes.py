"""Rutas de registro, login y logout."""

import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ...extensions import db, limiter
from ...forms.auth_forms import LoginForm, RegisterForm
from ...models import User
from ...services.audit import record_audit
from ..main.routes import safe_next_url

bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger("app.auth")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = User.normalize_email(form.email.data)
        username = form.username.data.strip()

        if db.session.scalar(db.select(User).where(User.email == email)):
            form.email.errors.append("Ya existe una cuenta con este email.")
        elif db.session.scalar(db.select(User).where(User.username == username)):
            form.username.errors.append("Ese nombre de usuario ya esta en uso.")
        else:
            user = User(email=email, username=username)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            record_audit("auth.register", user=user, metadata={"email": email})
            db.session.commit()
            login_user(user)
            logger.info("user_registered", extra={"user_id": user.id})
            flash("Cuenta creada correctamente.", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = User.normalize_email(form.email.data)
        user = db.session.scalar(db.select(User).where(User.email == email))

        if user is not None and user.is_active and user.check_password(
            form.password.data
        ):
            user.last_login_at = db.func.now()
            record_audit("auth.login_success", user=user, metadata={"email": email})
            db.session.commit()
            login_user(user, remember=form.remember.data)
            logger.info("login_success", extra={"user_id": user.id})
            flash("Sesion iniciada.", "success")
            next_url = safe_next_url(request.args.get("next"))
            return redirect(next_url or url_for("main.index"))

        record_audit(
            "auth.login_failed",
            status="failure",
            metadata={"email": email},
            error="Credenciales invalidas",
        )
        db.session.commit()
        logger.warning("login_failed", extra={"error": "Credenciales invalidas"})
        flash("Email o contraseña incorrectos.", "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    user = current_user._get_current_object()
    logout_user()
    record_audit("auth.logout", user=user)
    db.session.commit()
    logger.info("logout", extra={"user_id": user.id})
    flash("Sesion cerrada.", "info")
    return redirect(url_for("main.index"))
