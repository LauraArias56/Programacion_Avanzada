"""Manejadores de error de la aplicacion."""

import logging

from flask import render_template
from werkzeug.exceptions import HTTPException

from .extensions import db

logger = logging.getLogger("app.errors")


def register_error_handlers(app) -> None:
    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(503)
    def unavailable(error):
        return render_template("errors/503.html"), 503

    @app.errorhandler(Exception)
    def unhandled(error):
        if isinstance(error, HTTPException):
            return error
        logger.exception("unhandled_exception")
        db.session.rollback()
        return render_template("errors/500.html"), 500
