"""Pruebas del flujo de vision por computadora."""

import io

from app.extensions import db
from app.models import AuditLog, VisionPrediction
from app.services.api_client import ApiUnavailable, ApiValidationError
from tests.helpers import logout, register

def make_image():
    return (io.BytesIO(b"fake-image-bytes"), "cat.png", "image/png")


def _post_prediction(client, image=None, source="upload", headers=None):
    return client.post(
        "/vision/predict",
        data={"source": source, "image": image or make_image()},
        content_type="multipart/form-data",
        headers=headers or {},
        follow_redirects=True,
    )


def test_vision_page_requires_login(client):
    response = client.get("/vision")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_capture_page_and_model_info(app, client, vision_api):
    register(client)

    response = client.get("/vision")

    assert response.status_code == 200
    assert b"Activar camara" in response.data
    assert b"mobilenet_v3_small" in response.data
    assert b"88.6" in response.data


def test_predict_saves_vision_prediction_and_audit(app, client, vision_api):
    register(client)

    response = _post_prediction(client)

    assert response.status_code == 200
    assert b"gato" in response.data
    assert len(vision_api.predict_calls) == 1
    assert vision_api.predict_calls[0]["content_type"] == "image/png"

    with app.app_context():
        prediction = db.session.scalar(db.select(VisionPrediction))
        assert prediction is not None
        assert prediction.label == "cat"
        assert prediction.label_es == "gato"
        assert float(prediction.confidence) == 0.9123
        assert prediction.source == "upload"
        assert prediction.model_version == vision_api.model_version
        assert prediction.request_id == "vision-req-1"
        assert len(prediction.top_k) == 3

        audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.action == "vision.prediction.created"
            )
        )
        assert audit is not None
        assert audit.user_id == prediction.user_id


def test_predict_ajax_returns_redirect_url(app, client, vision_api):
    register(client)

    response = client.post(
        "/vision/predict",
        data={"source": "camera", "image": make_image()},
        content_type="multipart/form-data",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["label_es"] == "gato"
    assert body["redirect_url"].startswith("/vision")
    assert "prediction_id=" in body["redirect_url"]

    with app.app_context():
        prediction = db.session.scalar(db.select(VisionPrediction))
        assert prediction.source == "camera"


def test_predict_validation_error_is_shown_and_not_saved(app, client, vision_api):
    register(client)
    vision_api.predict_error = ApiValidationError("Imagen no valida.", 422)

    response = _post_prediction(client)

    assert response.status_code == 200
    assert b"Imagen no valida" in response.data

    with app.app_context():
        assert db.session.scalar(db.select(VisionPrediction)) is None
        audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.action == "vision.prediction_failed"
            )
        )
        assert audit is not None
        assert audit.status == "failure"


def test_predict_returns_503_when_vision_api_is_down(app, client, vision_api):
    register(client)
    vision_api.predict_error = ApiUnavailable("sin conexion")

    response = _post_prediction(client)

    assert response.status_code == 503
    assert b"no esta disponible" in response.data


def test_rejects_missing_or_unsupported_image(app, client, vision_api):
    register(client)

    missing = client.post("/vision/predict", data={"source": "upload"})
    assert missing.status_code == 302

    unsupported = client.post(
        "/vision/predict",
        data={
            "source": "upload",
            "image": (io.BytesIO(b"text"), "notes.txt", "text/plain"),
        },
        content_type="multipart/form-data",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert unsupported.status_code == 415
    assert vision_api.predict_calls == []


def test_history_lists_and_filters_predictions(app, client, vision_api):
    register(client)
    _post_prediction(client)

    page = client.get("/vision/history")
    assert page.status_code == 200
    assert b"gato" in page.data
    assert b"perro" in page.data

    empty = client.get("/vision/history?label=dog")
    assert b"No hay clasificaciones para estos filtros" in empty.data


def test_vision_prediction_ownership(app, client, vision_api):
    register(client)
    _post_prediction(client)

    with app.app_context():
        prediction_id = db.session.scalar(db.select(VisionPrediction.id))

    logout(client)
    register(client, username="other", email="other@example.com")
    forbidden = client.get(f"/vision?prediction_id={prediction_id}")
    assert forbidden.status_code == 404
