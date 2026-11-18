"""Pruebas basicas de la API."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_model_info(client):
    r = client.get("/model")
    assert r.status_code == 200
    body = r.json()
    assert body["target"] == "global_sales"
    assert "PS2" in body["allowed_platforms"]


def test_predict(client):
    r = client.post(
        "/predict",
        json={"platform": "PS4", "genre": "Action", "publisher": "Activision", "year": 2015},
    )
    assert r.status_code == 200
    pred = r.json()["prediction"]
    assert pred["predicted_sales_millions"] > 0
    assert pred["interval_95_millions"][0] <= pred["predicted_sales_millions"]


def test_predict_unknown_platform(client):
    r = client.post(
        "/predict",
        json={"platform": "PS9", "genre": "Action", "publisher": "X", "year": 2015},
    )
    assert r.status_code == 422
    assert "desconocida" in r.json()["detail"]


def test_predict_unknown_publisher_warns(client):
    r = client.post(
        "/predict",
        json={"platform": "PS4", "genre": "Action", "publisher": "Editorial Inventada", "year": 2015},
    )
    assert r.status_code == 200
    assert r.json()["prediction"]["warnings"]


def test_predict_batch(client):
    payload = {
        "games": [
            {"platform": "PS2", "genre": "Sports", "publisher": "Nintendo", "year": 2006},
            {"platform": "Wii", "genre": "Racing", "publisher": "Nintendo", "year": 2008},
        ]
    }
    r = client.post("/predict/batch", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert len(body["predictions"]) == 2
