"""Cliente HTTP hacia la Vision API (FastAPI) de CIFAR-10."""

import logging
import time
from threading import Lock

import httpx
from flask import current_app

from ..logging_config import request_id_var
from .api_client import ApiError, ApiUnavailable, ApiValidationError

logger = logging.getLogger("app.vision_client")


class VisionApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 20.0,
        retries: int = 2,
        model_info_ttl: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.retries = max(1, retries)
        self.model_info_ttl = model_info_ttl
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._lock = Lock()
        self._model_info: dict | None = None
        self._model_info_at = 0.0
        self._game_model_info: dict | None = None
        self._game_model_info_at = 0.0

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return f"Error {response.status_code} de la Vision API"
        detail = data.get("detail") if isinstance(data, dict) else None
        if isinstance(detail, list):
            detail = "; ".join(str(item) for item in detail)
        return str(detail) if detail else f"Error {response.status_code} de la Vision API"

    def _headers(self) -> dict:
        request_id = request_id_var.get()
        headers = {"Accept": "application/json"}
        if request_id:
            headers["X-Request-ID"] = request_id
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        files: dict | None = None,
    ):
        last_error: ApiUnavailable | None = None
        for attempt in range(1, self.retries + 1):
            started = time.perf_counter()
            try:
                response = self._client.request(
                    method,
                    path,
                    params=params,
                    files=files,
                    headers=self._headers(),
                )
            except httpx.HTTPError as exc:
                duration = round((time.perf_counter() - started) * 1000, 2)
                logger.warning(
                    "vision_api_request_failed",
                    extra={
                        "http_method": method,
                        "path": path,
                        "attempt": attempt,
                        "duration_ms": duration,
                        "error": str(exc),
                    },
                )
                last_error = ApiUnavailable(
                    f"No se pudo conectar con la Vision API ({exc.__class__.__name__})."
                )
                if attempt < self.retries:
                    time.sleep(0.2 * (2 ** (attempt - 1)))
                    continue
                raise last_error from exc

            duration = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "vision_api_request",
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
                    f"La Vision API devolvio un error interno ({response.status_code}).",
                    response.status_code,
                )
                if attempt < self.retries:
                    time.sleep(0.2 * (2 ** (attempt - 1)))
                    continue
                raise last_error

            if response.status_code >= 400:
                raise ApiValidationError(self._detail(response), response.status_code)

            try:
                return response.json()
            except ValueError as exc:
                raise ApiError("La Vision API devolvio una respuesta no valida.") from exc

        raise last_error or ApiUnavailable("La Vision API no esta disponible.")

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
                logger.warning("vision_model_info_stale", extra={"path": "/model"})
                return cached
            raise

        with self._lock:
            self._model_info = info
            self._model_info_at = time.monotonic()
        return info

    def game_model_info(self, force: bool = False) -> dict | None:
        with self._lock:
            cached = self._game_model_info
            cached_at = self._game_model_info_at
        if (
            not force
            and cached is not None
            and (time.monotonic() - cached_at) < self.model_info_ttl
        ):
            return cached

        try:
            info = self._request("GET", "/model/genres")
        except ApiValidationError as exc:
            if exc.status_code == 404:
                logger.warning("vision_game_model_endpoint_missing")
                return None
            raise
        except ApiUnavailable:
            if cached is not None:
                logger.warning(
                    "vision_game_model_info_stale", extra={"path": "/model/genres"}
                )
                return cached
            raise

        with self._lock:
            self._game_model_info = info
            self._game_model_info_at = time.monotonic()
        return info

    def predict_image(
        self,
        image_bytes: bytes,
        filename: str,
        content_type: str,
        top_k: int = 3,
    ) -> dict:
        return self._request(
            "POST",
            "/predict",
            params={"top_k": top_k},
            files={"file": (filename, image_bytes, content_type)},
        )

    def predict_game_genre(
        self,
        image_bytes: bytes,
        filename: str,
        content_type: str,
        top_k: int = 3,
    ) -> dict:
        return self._request(
            "POST",
            "/predict/genre",
            params={"top_k": top_k},
            files={"file": (filename, image_bytes, content_type)},
        )

    def close(self) -> None:
        self._client.close()


def get_vision_client() -> VisionApiClient:
    return current_app.extensions["vision_client"]
