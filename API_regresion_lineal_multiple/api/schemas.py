"""Contratos de entrada y salida de la API."""

from pydantic import BaseModel, ConfigDict, Field


class GameFeatures(BaseModel):
    """Datos de un videojuego para predecir sus ventas."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "PS4",
                "genre": "Action",
                "publisher": "Activision",
                "year": 2015,
            }
        }
    )

    platform: str = Field(..., description="Plataforma (debe existir en el dataset)")
    genre: str = Field(..., description="Genero (debe existir en el dataset)")
    publisher: str = Field(
        "Other", description="Editorial; si es desconocida se agrupa como 'Other'"
    )
    year: int = Field(..., ge=1970, le=2030, description="Ano de lanzamiento")


class BatchRequest(BaseModel):
    games: list[GameFeatures] = Field(..., min_length=1, max_length=1000)


class Prediction(BaseModel):
    predicted_sales_millions: float = Field(..., description="Ventas estimadas en millones")
    predicted_log_sales: float = Field(..., description="Valor en escala log1p")
    interval_95_millions: list[float] = Field(
        ..., description="Intervalo aproximado al 95% en millones"
    )
    warnings: list[str] = Field(default_factory=list)


class PredictionResponse(BaseModel):
    prediction: Prediction
    model_version: str


class BatchResponse(BaseModel):
    predictions: list[Prediction]
    count: int
    model_version: str


class ModelInfo(BaseModel):
    model_version: str
    target: str
    target_transform: str
    n_train: int
    n_features: int
    metrics: dict
    reference_levels: dict
    allowed_platforms: list[str]
    allowed_genres: list[str]
    year_range: list[int]
    excluded_columns: list[str]
    disclaimer: str
