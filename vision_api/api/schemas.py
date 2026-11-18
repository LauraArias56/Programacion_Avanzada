"""Contratos de entrada y salida del servicio de vision."""

from pydantic import BaseModel, Field


class TopKPrediction(BaseModel):
    class_id: int
    label: str
    label_es: str
    confidence: float = Field(..., ge=0, le=1)


class Prediction(BaseModel):
    label: str
    label_es: str
    confidence: float = Field(..., ge=0, le=1)
    top_k: list[TopKPrediction]
    latency_ms: float = Field(..., ge=0)


class PredictionResponse(BaseModel):
    prediction: Prediction
    model_version: str
    request_id: str | None = None


class ModelInfo(BaseModel):
    model_version: str
    architecture: str
    dataset: dict
    image_size: int
    num_classes: int
    classes: list[dict]
    metrics: dict
    preprocessing: dict
    disclaimer: str


class HealthResponse(BaseModel):
    status: str
    model_version: str
