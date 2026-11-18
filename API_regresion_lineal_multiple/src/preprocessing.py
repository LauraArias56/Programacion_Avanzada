"""Limpieza y construccion de la matriz de diseno.

Reglas aplicadas:
  1. `year` se imputa con la mediana de su plataforma (y si no hay, la global)
     y se centra en su media para que el intercepto sea interpretable.
  2. `publisher` se agrupa: los TOP_PUBLISHERS mas frecuentes y el resto -> "Other".
  3. La variable objetivo se transforma con log1p para corregir el sesgo.
  4. Las categoricas pasan a dummies tomando como referencia la categoria
     mas frecuente (evita la trampa de las dummies y coeficientes contra
     una categoria rara).
"""

import numpy as np
import pandas as pd

from . import config


class Preprocessor:
    """Ajusta reglas sobre train y las reaplica sobre test."""

    def __init__(
        self,
        target: str = config.TARGET,
        top_publishers: int = config.TOP_PUBLISHERS,
        numeric_features=None,
        categorical_features=None,
    ):
        self.target = target
        self.top_publishers = top_publishers
        self.numeric_features = numeric_features or config.NUMERIC_FEATURES
        self.categorical_features = categorical_features or config.CATEGORICAL_FEATURES

        # Estado aprendido en fit()
        self.publisher_levels_ = None
        self.year_by_platform_ = None
        self.year_median_ = None
        self.year_mean_ = None
        self.reference_levels_ = {}
        self.columns_ = None

    # ------------------------------------------------------------------ API
    def fit_transform(self, df: pd.DataFrame):
        """Aprende las reglas con el conjunto de entrenamiento."""
        data = df.copy()

        self.year_by_platform_ = data.groupby("platform")["year"].median()
        self.year_median_ = data["year"].median()
        self.year_mean_ = data["year"].mean()
        self.publisher_levels_ = (
            data["publisher"].value_counts().head(self.top_publishers).index.tolist()
        )

        data = self._clean(data)
        self.reference_levels_ = {
            col: data[col].mode().iloc[0] for col in self.categorical_features
        }
        X = self._encode(data)
        self.columns_ = list(X.columns)
        y = data[config.TARGET_LOG]
        return X, y

    def transform(self, df: pd.DataFrame):
        """Aplica las reglas aprendidas (sin reajustarlas)."""
        data = self._clean(df.copy(), with_target=True)
        X = self._encode(data).reindex(columns=self.columns_, fill_value=0.0)
        y = data[config.TARGET_LOG]
        return X, y

    def transform_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Solo construye X (para servir predicciones sin la variable objetivo)."""
        if self.columns_ is None:
            raise ValueError("Primero hay que llamar a fit_transform().")

        data = self._clean(df.copy(), with_target=False)
        return self._encode(data).reindex(columns=self.columns_, fill_value=0.0)

    # ------------------------------------------------------------- interno
    def _clean(self, data: pd.DataFrame, with_target: bool = True) -> pd.DataFrame:
        # 1) year
        data["year"] = data["year"].fillna(
            data["platform"].map(self.year_by_platform_)
        )
        data["year"] = data["year"].fillna(self.year_median_)
        data["year"] = data["year"] - self.year_mean_  # centrado

        # 2) publisher
        data["publisher"] = data["publisher"].fillna("Unknown")
        data["publisher"] = data["publisher"].where(
            data["publisher"].isin(self.publisher_levels_), "Other"
        )

        if not with_target:
            return data

        # 3) objetivo en escala logaritmica
        data[config.TARGET_LOG] = np.log1p(data[self.target])

        # 4) solo filas con objetivo valido
        return data.dropna(subset=[config.TARGET_LOG])

    def _encode(self, data: pd.DataFrame) -> pd.DataFrame:
        numeric = data[self.numeric_features].astype(float)
        frames = [numeric]

        for col in self.categorical_features:
            dummies = pd.get_dummies(data[col], prefix=col, dtype=float)
            reference = f"{col}_{self.reference_levels_[col]}"
            if reference in dummies.columns:
                dummies = dummies.drop(columns=[reference])
            frames.append(dummies)

        return pd.concat(frames, axis=1)
