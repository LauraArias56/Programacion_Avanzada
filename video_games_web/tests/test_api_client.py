"""Pruebas del cliente HTTP con un transporte simulado."""

import httpx
import pytest

from app.services.api_client import ApiClient, ApiUnavailable, ApiValidationError


def make_client(handler, retries=1):
    client = ApiClient(
        "http://api.test", timeout=1, retries=retries, model_info_ttl=300
    )
    client._client.close()
    client._client = httpx.Client(
        base_url="http://api.test",
        transport=httpx.MockTransport(handler),
        timeout=1,
    )
    return client


def test_predict_success():
    def handler(request):
        assert request.url.path == "/predict"
        return httpx.Response(
            200,
            json={
                "prediction": {
                    "predicted_sales_millions": 0.5,
                    "predicted_log_sales": 0.4,
                    "interval_95_millions": [0.0, 1.0],
                    "warnings": [],
                },
                "model_version": "v1",
            },
        )

    client = make_client(handler)

    result = client.predict({"platform": "PS4"})

    assert result["model_version"] == "v1"
    assert result["prediction"]["predicted_sales_millions"] == 0.5


def test_validation_error_is_raised():
    def handler(request):
        return httpx.Response(
            422, json={"detail": "Plataforma desconocida: 'PS9'"}
        )

    client = make_client(handler)

    with pytest.raises(ApiValidationError) as exc_info:
        client.predict({"platform": "PS9"})

    assert exc_info.value.status_code == 422
    assert "PS9" in str(exc_info.value)


def test_server_error_raises_unavailable():
    def handler(request):
        return httpx.Response(500, json={"detail": "boom"})

    client = make_client(handler)

    with pytest.raises(ApiUnavailable) as exc_info:
        client.predict({"platform": "PS4"})

    assert exc_info.value.status_code == 500


def test_model_info_is_cached():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "model_version": "v1",
                "allowed_platforms": ["PS4"],
                "allowed_genres": ["Action"],
                "year_range": [1980, 2020],
                "metrics": {},
            },
        )

    client = make_client(handler)

    first = client.model_info()
    second = client.model_info()

    assert first == second
    assert calls == ["/model"]


def test_connection_error_raises_unavailable():
    def handler(request):
        raise httpx.ConnectError("sin conexion", request=request)

    client = make_client(handler)

    with pytest.raises(ApiUnavailable):
        client.health()
