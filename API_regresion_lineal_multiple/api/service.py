"""Logica de negocio del servicio: validacion y prediccion."""

import pandas as pd

from src import config
from src.model_bundle import ModelBundle

from .schemas import GameFeatures, Prediction


class ModelService:
    """Carga el artefacto una sola vez y atiende peticiones."""

    def __init__(self, artifact_path=config.ARTIFACT_PATH):
        self.bundle = ModelBundle.load(artifact_path)
        self.meta = self.bundle.metadata
        self.version = self.meta["version"]

        self._platforms = {p.lower(): p for p in self.meta["allowed_platforms"]}
        self._genres = {g.lower(): g for g in self.meta["allowed_genres"]}

    # ------------------------------------------------------------ validacion
    def _resolve(self, game: GameFeatures) -> tuple[dict, list[str]]:
        warnings: list[str] = []

        platform = self._platforms.get(game.platform.strip().lower())
        if platform is None:
            raise ValueError(
                f"Plataforma desconocida: '{game.platform}'. "
                f"Validas: {', '.join(self.meta['allowed_platforms'])}"
            )

        genre = self._genres.get(game.genre.strip().lower())
        if genre is None:
            raise ValueError(
                f"Genero desconocido: '{game.genre}'. "
                f"Validos: {', '.join(self.meta['allowed_genres'])}"
            )

        publisher = game.publisher.strip()
        if publisher.lower() not in {p.lower() for p in self.meta["publisher_levels"]}:
            warnings.append(
                f"Editorial '{publisher}' no vista en entrenamiento; "
                "se agrupa como 'Other'."
            )
            publisher = "Other"

        year_min, year_max = self.meta["year_range"]
        if not year_min <= game.year <= year_max:
            warnings.append(
                f"Ano {game.year} fuera del rango de entrenamiento "
                f"({year_min}-{year_max}); es una extrapolacion."
            )

        return {
            "platform": platform,
            "genre": genre,
            "publisher": publisher,
            "year": game.year,
        }, warnings

    # ------------------------------------------------------------ prediccion
    def predict_one(self, game: GameFeatures) -> Prediction:
        row, warnings = self._resolve(game)
        return self._predict_frame(pd.DataFrame([row]), [warnings])[0]

    def predict_many(self, games: list[GameFeatures]) -> list[Prediction]:
        rows, warnings = [], []
        for game in games:
            row, w = self._resolve(game)
            rows.append(row)
            warnings.append(w)
        return self._predict_frame(pd.DataFrame(rows), warnings)

    def _predict_frame(self, frame: pd.DataFrame, warnings: list[list[str]]) -> list[Prediction]:
        log_pred = self.bundle.predict_log(frame)
        mean, low, high = self.bundle.predict_with_interval(frame)

        return [
            Prediction(
                predicted_sales_millions=round(float(m), 4),
                predicted_log_sales=round(float(lp), 4),
                interval_95_millions=[round(float(lo), 4), round(float(hi), 4)],
                warnings=w,
            )
            for lp, m, lo, hi, w in zip(log_pred, mean, low, high, warnings)
        ]
