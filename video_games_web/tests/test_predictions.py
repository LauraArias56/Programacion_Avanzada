"""Pruebas del flujo de prediccion e historial."""

from app.extensions import db
from app.models import AuditLog, Prediction
from app.services.api_client import ApiUnavailable, ApiValidationError
from tests.helpers import logout, register

GAME = {
    "platform": "PS4",
    "genre": "Action",
    "publisher": "Activision",
    "year": 2015,
}


def test_predict_saves_prediction_and_audit(app, client, api):
    register(client)

    response = client.post("/predict", data=GAME, follow_redirects=True)

    assert response.status_code == 200
    assert b"Ventas estimadas" in response.data
    assert api.predict_calls == [GAME]

    with app.app_context():
        prediction = db.session.scalar(db.select(Prediction))
        assert prediction is not None
        assert prediction.platform == "PS4"
        assert float(prediction.predicted_sales_millions) == 0.6827
        assert prediction.model_version == api.model_version
        assert prediction.request_id

        audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "prediction.created")
        )
        assert audit is not None
        assert audit.user_id == prediction.user_id


def test_predict_validation_error_is_shown_and_not_saved(app, client, api):
    register(client)
    api.predict_error = ApiValidationError("Plataforma desconocida: 'PS9'", 422)

    response = client.post(
        "/predict",
        data={**GAME, "platform": "PS4"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Plataforma desconocida" in response.data

    with app.app_context():
        assert db.session.scalar(db.select(Prediction)) is None
        audit = db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "prediction.failed")
        )
        assert audit is not None
        assert audit.status == "failure"


def test_predict_returns_503_when_api_is_down(app, client, api):
    register(client)
    api.info_error = ApiUnavailable("sin conexion")

    response = client.get("/predict")

    assert response.status_code == 503
    assert b"no esta disponible" in response.data


def test_history_filters_and_ownership(app, client, api):
    register(client)
    client.post("/predict", data=GAME, follow_redirects=True)

    page = client.get("/history?platform=PS4&year=2015")
    assert page.status_code == 200
    assert b"PS4" in page.data

    empty = client.get("/history?platform=Wii")
    assert b"No hay predicciones para estos filtros" in empty.data

    with app.app_context():
        prediction_id = db.session.scalar(db.select(Prediction.id))

    logout(client)
    register(client, username="other", email="other@example.com")
    forbidden = client.get(f"/history/{prediction_id}")
    assert forbidden.status_code == 404


def test_history_export_csv(app, client):
    register(client)
    client.post("/predict", data=GAME, follow_redirects=True)

    response = client.get("/history/export.csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"plataforma" in response.data
    assert b"PS4" in response.data
