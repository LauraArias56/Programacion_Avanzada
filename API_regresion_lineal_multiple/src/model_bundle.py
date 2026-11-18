"""Artefacto autocontenido listo para servir por API.

Guarda el preprocesador ajustado + los coeficientes en un solo archivo.
Predecir no requiere reentrenar ni volver a usar statsmodels.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import config


class ModelBundle:
    """Preprocesador + coeficientes + metadatos."""

    def __init__(
        self,
        preprocessor,
        coefficients: pd.Series,
        intercept: float,
        sigma: float,
        metadata: dict,
    ):
        self.preprocessor = preprocessor
        self.coefficients = coefficients
        self.intercept = float(intercept)
        self.sigma = float(sigma)
        self.metadata = metadata

    # ------------------------------------------------------------ inferencia
    def predict_log(self, df: pd.DataFrame) -> np.ndarray:
        """Prediccion en la escala del modelo (log1p)."""
        X = self.preprocessor.transform_features(df)
        return X[self.coefficients.index].to_numpy(dtype=float) @ self.coefficients.to_numpy(
            dtype=float
        ) + self.intercept

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Prediccion en millones de unidades."""
        return np.expm1(self.predict_log(df))

    def predict_with_interval(self, df: pd.DataFrame, z: float = 1.96):
        """Prediccion + intervalo aproximado al 95% (en millones)."""
        log_pred = self.predict_log(df)
        low = np.clip(np.expm1(log_pred - z * self.sigma), 0, None)
        high = np.expm1(log_pred + z * self.sigma)
        return np.expm1(log_pred), low, high

    # ------------------------------------------------------------ persistencia
    def save(self, path=config.ARTIFACT_PATH) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path=config.ARTIFACT_PATH) -> "ModelBundle":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el artefacto {path}. Ejecuta primero: python train.py"
            )
        return joblib.load(path)

    def info(self) -> dict:
        """Metadatos serializables (sin objetos pesados)."""
        return {
            "metadata": self.metadata,
            "intercept": self.intercept,
            "sigma_log": self.sigma,
            "n_coefficients": int(len(self.coefficients)),
        }
