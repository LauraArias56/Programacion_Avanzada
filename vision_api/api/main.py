"""API HTTP para clasificar imagenes de CIFAR-10.

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


def create_app(service: VisionModelService | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.service is None:
            app.state.service = VisionModelService()
        yield

    app = FastAPI(
        title="Video Games Vision API",
        description=(
            "Clasificador de imagenes CIFAR-10 con Transfer Learning "
            "(MobileNetV3-Small preentrenado en ImageNet)."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.service = service

    def get_service(request: Request) -> VisionModelService:
        return request.app.state.service

    @app.get("/", tags=["info"])
    def root():
        return {
            "service": "Video Games Vision API",
            "docs": "/docs",
            "endpoints": ["/health", "/model", "/predict"],
        }

    @app.get("/health", response_model=HealthResponse, tags=["info"])
    def health(request: Request):
        svc = get_service(request)
        return {"status": "ok", "model_version": svc.model_version}

    @app.get("/model", response_model=ModelInfo, tags=["info"])
    def model_info(request: Request):
        return get_service(request).info()

    @app.post("/predict", response_model=PredictionResponse, tags=["vision"])
    async def predict(
        request: Request,
        file: UploadFile = File(..., description="Imagen JPG, PNG o WebP"),
        top_k: int = Query(3, ge=1, le=10),
    ):
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

        svc = get_service(request)
        started = perf_counter()
        prediction = svc.predict(image, top_k=top_k)
        prediction["latency_ms"] = round((perf_counter() - started) * 1000, 2)

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

    return app


app = create_app()
