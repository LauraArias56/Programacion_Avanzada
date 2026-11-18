"""Aplicacion Flask que consume la API de prediccion de ventas."""

from flask import Flask

from .cli import register_cli
from .config import Config
from .errors import register_error_handlers
from .extensions import csrf, db, limiter, login_manager, migrate
from .hooks import register_hooks
from .logging_config import configure_logging
from .services.api_client import ApiClient
from .services.vision_client import VisionApiClient


def create_app(config_object=Config, **overrides) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    if overrides:
        app.config.update(overrides)

    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from . import models  # noqa: F401  (registra los modelos en metadata)
    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    app.extensions["api_client"] = ApiClient(
        app.config["API_BASE_URL"],
        timeout=app.config["API_TIMEOUT"],
        retries=app.config["API_RETRIES"],
        model_info_ttl=app.config["MODEL_INFO_TTL"],
    )
    app.extensions["vision_client"] = VisionApiClient(
        app.config["VISION_API_BASE_URL"],
        timeout=app.config["VISION_API_TIMEOUT"],
        retries=app.config["VISION_API_RETRIES"],
        model_info_ttl=app.config["VISION_MODEL_INFO_TTL"],
    )

    from .blueprints.admin.routes import bp as admin_bp
    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.main.routes import bp as main_bp
    from .blueprints.vision.routes import bp as vision_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(vision_bp)

    register_hooks(app)
    register_error_handlers(app)
    register_cli(app)

    return app
