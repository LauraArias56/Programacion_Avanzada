"""Cliente HTTP hacia la API FastAPI de predicciones."""

import logging
import time
from threading import Lock

import httpx
from flask import current_app

from ..logging_config import request_id_var

logger = logging.getLogger("app.api_client")


class ApiError(Exception):
    """Error generico de comunicacion con la API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ApiValidationError(ApiError):
    """La API rechazo los datos de entrada (4xx)."""


class ApiUnavailable(ApiError):
    """La API no responde o devuelve errores 5xx."""


class ApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        retries: int = 3,
        model_info_ttl: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.retries = max(1, retries)
        self.model_info_ttl = model_info_ttl
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._lock = Lock()
        self._model_info: dict | None = None
        self._model_info_at = 0.0

    # ------------------------------------------------------------------ HTTP
    @staticmethod
    def _detail(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return f"Error {response.status_code} de la API"
        detail = data.get("detail") if isinstance(data, dict) else None
        if isinstance(detail, list):
            detail = "; ".join(str(item) for item in detail)
        return str(detail) if detail else f"Error {response.status_code} de la API"

    def _headers(self) -> dict:
        request_id = request_id_var.get()
        return {"X-Request-ID": request_id} if request_id else {}

    def _request(self, method: str, path: str, json: dict | None = None):
        last_error: ApiUnavailable | None = None
        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self._client.request(
                    method, path, json=json, headers=self._headers()
                )
            except httpx.HTTPError as exc:
                duration = round((time.perf_counter() - started) * 1000, 2)
                logger.warning(
                    "api_request_failed",
                    extra={
                        "http_method": method,
                        "path": path,
                        "attempt": attempt,
                        "duration_ms": duration,
                        "error": str(exc),
                    },
                )
                last_error = ApiUnavailable(
                    f"No se pudo conectar con la API ({exc.__class__.__name__})."
                )
                if attempt < self.retries:
                    time.sleep(0.2 * (2 ** (attempt - 1)))
                    continue
                raise last_error from exc

            duration = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "api_request",
                extra={
                    "http_method": method,
                    "path": path,
                    "status": response.status_code,
                    "attempt": attempt,
                    "duration_ms": duration,
                },
            )

            if response.status_code >= 500:
                last_error = ApiUnavailable(
                    f"La API devolvio un error interno ({response.status_code}).",
                    response.status_code,
                )
                if attempt < self.retries:
                    time.sleep(0.2 * (2 ** (attempt - 1)))
                    continue
                raise last_error

            if response.status_code >= 400:
                raise ApiValidationError(
                    self._detail(response), response.status_code
                )

            try:
                return response.json()
            except ValueError as exc:
                raise ApiError("La API devolvio una respuesta no valida.") from exc

        raise last_error or ApiUnavailable("La API no esta disponible.")

    # ------------------------------------------------------------- operaciones
    def health(self) -> dict:
        return self._request("GET", "/health")

    def model_info(self, force: bool = False) -> dict:
        with self._lock:
            cached = self._model_info
            cached_at = self._model_info_at
        if (
            not force
            and cached is not None
            and (time.monotonic() - cached_at) < self.model_info_ttl
        ):
            return cached

        try:
            info = self._request("GET", "/model")
        except ApiUnavailable:
            if cached is not None:
                logger.warning("api_model_info_stale", extra={"path": "/model"})
                return cached
            raise

        with self._lock:
            self._model_info = info
            self._model_info_at = time.monotonic()
        return info

    def predict(self, game: dict) -> dict:
        return self._request("POST", "/predict", json=game)

    def close(self) -> None:
        self._client.close()


def get_api_client() -> ApiClient:
    return current_app.extensions["api_client"]
