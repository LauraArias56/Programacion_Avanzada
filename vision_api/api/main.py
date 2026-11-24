"""API HTTP para clasificar imagenes CIFAR-10 y generos de videojuego.

Arrancar en local:
    python -m uvicorn api.main:app --port 8100

Documentacion interactiva:
    http://localhost:8100/docs
"""

import io
import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from src import config

from .game_service import GameGenreModelService
from .schemas import (
    HealthResponse,
    ModelInfo,
    PredictionResponse,
)
from .service import VisionModelService

logger = logging.getLogger("vision.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def _load_image(file: UploadFile) -> Image.Image:
    content_type = (file.content_type or "").lower()
    if content_type not in config.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                "Formato no soportado. Usa JPG, PNG o WebP "
                f"(recibido: {content_type or 'desconocido'})."
            ),
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="La imagen esta vacia.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"La imagen supera el limite de {config.MAX_UPLOAD_MB} MB.",
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=422, detail="El archivo no es una imagen valida."
        ) from exc
    return image


def create_app(
    service: VisionModelService | None = None,
    game_service: GameGenreModelService | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.service is None:
            app.state.service = VisionModelService()
        if app.state.game_service is None:
            try:
                app.state.game_service = GameGenreModelService()
            except FileNotFoundError as exc:
                logger.warning("game_genre_model_unavailable: %s", exc)
                app.state.game_service = None
        yield

    app = FastAPI(
        title="Video Games Vision API",
        description=(
            "Clasificador CIFAR-10 y clasificador de generos de videojuego "
            "con Transfer Learning (MobileNetV3-Small preentrenado en ImageNet)."
        ),
        version="1.1.0",
        lifespan=lifespan,
    )
    app.state.service = service
    app.state.game_service = game_service

    def get_service(request: Request) -> VisionModelService:
        return request.app.state.service

    def get_game_service(request: Request) -> GameGenreModelService:
        svc = request.app.state.game_service
        if svc is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Modelo de generos no disponible. "
                    "Entrena con train_game_genres.py."
                ),
            )
        return svc

    @app.get("/", tags=["info"])
    def root():
        return {
            "service": "Video Games Vision API",
            "docs": "/docs",
            "endpoints": [
                "/health",
                "/model",
                "/model/genres",
                "/predict",
                "/predict/genre",
            ],
        }

    @app.get("/health", response_model=HealthResponse, tags=["info"])
    def health(request: Request):
        svc = get_service(request)
        game_svc = request.app.state.game_service
        return {
            "status": "ok",
            "model_version": svc.model_version,
            "game_genre_available": game_svc is not None,
            "game_genre_model_version": (
                game_svc.model_version if game_svc is not None else None
            ),
        }

    @app.get("/model", response_model=ModelInfo, tags=["info"])
    def model_info(request: Request):
        return get_service(request).info()

    @app.get("/model/genres", response_model=ModelInfo, tags=["info"])
    def game_model_info(request: Request):
        return get_game_service(request).info()

    @app.post("/predict", response_model=PredictionResponse, tags=["vision"])
    async def predict(
        request: Request,
        file: UploadFile = File(..., description="Imagen JPG, PNG o WebP"),
        top_k: int = Query(3, ge=1, le=10),
    ):
        image = await _load_image(file)
        svc = get_service(request)
        started = perf_counter()
        prediction = svc.predict(image, top_k=top_k)
        prediction["latency_ms"] = round((perf_counter() - started) * 1000, 2)
        prediction["kind"] = "cifar10"

        request_id = request.headers.get("X-Request-ID")
        logger.info(
            "vision_prediction label=%s confidence=%.4f latency_ms=%.2f request_id=%s",
            prediction["label"],
            prediction["confidence"],
            prediction["latency_ms"],
            request_id or "-",
        )

        return PredictionResponse(
            prediction=prediction,
            model_version=svc.model_version,
            request_id=request_id,
        )

    @app.post("/predict/genre", response_model=PredictionResponse, tags=["vision"])
    async def predict_genre(
        request: Request,
        file: UploadFile = File(..., description="Portada o captura JPG, PNG o WebP"),
        top_k: int = Query(3, ge=1, le=11),
    ):
        image = await _load_image(file)
        svc = get_game_service(request)
        started = perf_counter()
        prediction = svc.predict(image, top_k=top_k)
        prediction["latency_ms"] = round((perf_counter() - started) * 1000, 2)
        prediction["kind"] = "game_genre"

        request_id = request.headers.get("X-Request-ID")
        logger.info(
            "game_genre_prediction label=%s confidence=%.4f latency_ms=%.2f "
            "request_id=%s",
            prediction["label"],
            prediction["confidence"],
            prediction["latency_ms"],
            request_id or "-",
        )

        return PredictionResponse(
            prediction=prediction,
            model_version=svc.model_version,
            request_id=request_id,
        )

    return app


app = create_app()
