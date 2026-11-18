"""Pruebas del flujo de vision por computadora."""

import io

from app.extensions import db
from app.models import AuditLog, Prediction, VisionPrediction
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


def test_predict_saves_vision_and_sales_prediction(app, client, vision_api, api):
    register(client)

    response = _post_prediction(client)

    assert response.status_code == 200
    assert b"gato" in response.data
    assert b"Ventas globales estimadas" in response.data
    assert b"0.683" in response.data
    assert len(vision_api.predict_calls) == 1
    assert vision_api.predict_calls[0]["content_type"] == "image/png"
    assert api.predict_calls == [
        {
            "platform": "Wii",
            "genre": "Misc",
            "publisher": "Nintendo",
            "year": 2015,
        }
    ]

    with app.app_context():
        prediction = db.session.scalar(db.select(VisionPrediction))
        assert prediction is not None
        assert prediction.label == "cat"
        assert prediction.label_es == "gato"
        assert float(prediction.confidence) == 0.9123
        assert prediction.source == "upload"
        assert prediction.model_version == vision_api.model_version
        assert prediction.request_id == "vision-req-1"
        assert prediction.theme == "mascotas y familia"
        assert len(prediction.top_k) == 3
        assert prediction.prediction_id is not None

        sale = db.session.get(Prediction, prediction.prediction_id)
        assert sale is not None
        assert sale.platform == "Wii"
        assert sale.genre == "Misc"
        assert sale.publisher == "Nintendo"
        assert sale.year == 2015
        assert float(sale.predicted_sales_millions) == 0.6827
        assert sale.vision_prediction is prediction

        audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.action == "vision.prediction.created"
            )
        )
        assert audit is not None
        assert audit.user_id == prediction.user_id
        assert audit.meta["sales_prediction_id"] == sale.id

        sales_audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "prediction.created")
        )
        assert sales_audit is not None
        assert sales_audit.meta["source"] == "vision"


def test_predict_ajax_returns_sales_and_redirect_url(app, client, vision_api):
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
    assert body["theme"] == "mascotas y familia"
    assert body["profile"] == {
        "platform": "Wii",
        "genre": "Misc",
        "publisher": "Nintendo",
        "year": 2015,
    }
    assert body["predicted_sales_millions"] == 0.6827
    assert body["redirect_url"].startswith("/vision")
    assert "prediction_id=" in body["redirect_url"]

    with app.app_context():
        prediction = db.session.scalar(db.select(VisionPrediction))
        assert prediction.source == "camera"
        assert prediction.sales_prediction is not None


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


def test_predict_returns_503_when_sales_api_is_down(app, client, vision_api, api):
    register(client)
    api.predict_error = ApiUnavailable("sin conexion")

    response = _post_prediction(client)

    assert response.status_code == 503

    with app.app_context():
        assert db.session.scalar(db.select(VisionPrediction)) is None
        assert db.session.scalar(db.select(Prediction)) is None
        audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.action == "vision.prediction_failed"
            )
        )
        assert audit is not None
        assert audit.meta["stage"] == "sales_prediction"


def test_recalculate_updates_linked_sales(app, client, vision_api, api):
    register(client)
    _post_prediction(client)

    with app.app_context():
        vision = db.session.scalar(db.select(VisionPrediction))
        vision_id = vision.id
        sale_id = vision.prediction_id

    response = client.post(
        f"/vision/{vision_id}/recalculate",
        data={
            "platform": "PS4",
            "genre": "Sports",
            "publisher": "Electronic Arts",
            "year": 2018,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Perfil actualizado y ventas recalculadas" in response.data

    with app.app_context():
        vision = db.session.get(VisionPrediction, vision_id)
        sale = db.session.get(Prediction, sale_id)
        assert vision.sales_prediction is sale
        assert sale.platform == "PS4"
        assert sale.genre == "Sports"
        assert sale.publisher == "Electronic Arts"
        assert sale.year == 2018
        assert api.predict_calls[-1] == {
            "platform": "PS4",
            "genre": "Sports",
            "publisher": "Electronic Arts",
            "year": 2018,
        }

        audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.action == "vision.prediction.recalculated"
            )
        )
        assert audit is not None
        assert audit.meta["input"]["platform"] == "PS4"


def test_recalculate_rejects_invalid_profile(app, client, vision_api):
    register(client)
    _post_prediction(client)

    with app.app_context():
        vision_id = db.session.scalar(db.select(VisionPrediction.id))

    response = client.post(
        f"/vision/{vision_id}/recalculate",
        data={
            "platform": "PS9",
            "genre": "Sports",
            "publisher": "Electronic Arts",
            "year": 2018,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"plataforma valida" in response.data


def test_recalculate_prediction_ownership(app, client, vision_api):
    register(client)
    _post_prediction(client)

    with app.app_context():
        vision_id = db.session.scalar(db.select(VisionPrediction.id))

    logout(client)
    register(client, username="other", email="other@example.com")
    response = client.post(
        f"/vision/{vision_id}/recalculate",
        data={
            "platform": "PS4",
            "genre": "Sports",
            "publisher": "Electronic Arts",
            "year": 2018,
        },
    )
    assert response.status_code == 404


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
    assert b"Ventas (M)" in page.data
    assert b"0.683" in page.data
    assert b"Wii" in page.data

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
