"""Fixtures comunes de pytest."""

import pytest

from app import create_app
from app.extensions import db
from tests.fakes import FakeApiClient, FakeVisionClient


@pytest.fixture
def app(tmp_path):
    app = create_app(
        TESTING=True,
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
        LOG_DIR=str(tmp_path / "logs"),
        LOG_LEVEL="WARNING",
    )
    app.extensions["api_client"] = FakeApiClient()
    app.extensions["vision_client"] = FakeVisionClient()

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def api(app):
    return app.extensions["api_client"]


@pytest.fixture
def vision_api(app):
    return app.extensions["vision_client"]
