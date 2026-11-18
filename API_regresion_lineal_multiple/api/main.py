"""API HTTP para consumir el modelo de regresion lineal multiple.

Arrancar:
    uvicorn api.main:app --reload --port 8000

Documentacion interactiva:
    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from src import config

from .schemas import (
    BatchRequest,
    BatchResponse,
    GameFeatures,
    ModelInfo,
    PredictionResponse,
)
from .service import ModelService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service = ModelService()
    yield


app = FastAPI(
    title="Video Games Sales API",
    description=(
        "Predice ventas globales (millones) con una regresion lineal multiple. "
        "Modelo: log1p(global_sales) ~ year + platform + genre + publisher."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service(request: Request) -> ModelService:
    return request.app.state.service


@app.get("/", tags=["info"])
def root():
    return {
        "service": "Video Games Sales API",
        "docs": "/docs",
        "endpoints": ["/health", "/model", "/predict", "/predict/batch"],
    }


@app.get("/health", tags=["info"])
def health(request: Request):
    return {"status": "ok", "model_version": get_service(request).version}


@app.get("/model", response_model=ModelInfo, tags=["info"])
def model_info(request: Request):
    meta = get_service(request).meta
    return ModelInfo(
        model_version=meta["version"],
        target=meta["target"],
        target_transform=meta["target_transform"],
        n_train=meta["n_train"],
        n_features=meta["n_features"],
        metrics=meta["metrics"],
        reference_levels=meta["reference_levels"],
        allowed_platforms=meta["allowed_platforms"],
        allowed_genres=meta["allowed_genres"],
        year_range=meta["year_range"],
        excluded_columns=meta["excluded_columns"],
        disclaimer=(
            "Prediccion aproximada. R2 test ~0.25 en escala log: el modelo "
            "explica una parte de la variabilidad, no sustituye un estudio de mercado."
        ),
    )


@app.post("/predict", response_model=PredictionResponse, tags=["prediccion"])
def predict(game: GameFeatures, request: Request):
    try:
        prediction = get_service(request).predict_one(game)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PredictionResponse(
        prediction=prediction, model_version=get_service(request).version
    )


@app.post("/predict/batch", response_model=BatchResponse, tags=["prediccion"])
def predict_batch(payload: BatchRequest, request: Request):
    service = get_service(request)
    try:
        predictions = service.predict_many(payload.games)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return BatchResponse(
        predictions=predictions, count=len(predictions), model_version=service.version
    )
