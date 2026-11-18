"""Pruebas de los endpoints de la Vision API con un servicio simulado."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from src import config


class FakeService:
    model_version = "test-vision"

    def info(self):
        return {
            "model_version": self.model_version,
            "architecture": "mobilenet_v3_small",
            "dataset": {"name": "CIFAR-10"},
            "image_size": 160,
            "num_classes": 10,
            "classes": [{"id": 3, "label": "cat", "label_es": "gato"}],
            "metrics": {"test_accuracy": 0.88},
            "preprocessing": {"resize": [160, 160]},
            "disclaimer": "Demostracion.",
        }

    def predict(self, image, top_k=3):
        return {
            "label": "cat",
            "label_es": "gato",
            "confidence": 0.91,
            "top_k": [
                {
                    "class_id": 3,
                    "label": "cat",
                    "label_es": "gato",
                    "confidence": 0.91,
                }
            ],
        }


@pytest.fixture
def client():
    with TestClient(create_app(service=FakeService())) as test_client:
        yield test_client


def image_bytes(fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(buffer, format=fmt)
    return buffer.getvalue()


def test_health_and_model(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["model_version"] == "test-vision"

    info = client.get("/model")
    assert info.status_code == 200
    assert info.json()["num_classes"] == 10


def test_predict_returns_top_k_and_request_id(client):
    response = client.post(
        "/predict?top_k=1",
        files={"file": ("cat.png", image_bytes(), "image/png")},
        headers={"X-Request-ID": "req-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-123"
    assert body["prediction"]["label_es"] == "gato"
    assert body["prediction"]["confidence"] == 0.91
    assert body["prediction"]["latency_ms"] >= 0


def test_predict_rejects_unsupported_content_type(client):
    response = client.post(
        "/predict",
        files={"file": ("notes.txt", b"no soy una imagen", "text/plain")},
    )

    assert response.status_code == 415


def test_predict_rejects_empty_and_invalid_images(client):
    empty = client.post(
        "/predict", files={"file": ("empty.png", b"", "image/png")}
    )
    assert empty.status_code == 400

    invalid = client.post(
        "/predict", files={"file": ("bad.png", b"not-an-image", "image/png")}
    )
    assert invalid.status_code == 422


def test_predict_rejects_oversized_upload(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10)

    response = client.post(
        "/predict", files={"file": ("big.png", image_bytes(), "image/png")}
    )

    assert response.status_code == 413
