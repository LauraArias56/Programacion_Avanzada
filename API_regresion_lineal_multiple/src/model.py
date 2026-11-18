"""Modelo de regresion lineal multiple sobre statsmodels (OLS)."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class MultipleLinearRegression:
    """Ajusta y evalua un OLS.

    Ejemplo
    -------
    >>> model = MultipleLinearRegression().fit(X_train, y_train)
    >>> pred = model.predict(X_test)
    >>> model.metrics(y_test, pred)
    """

    def __init__(self, cov_type: str | None = "HC3"):
        self.cov_type = cov_type
        self.results_ = None
        self.feature_names_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """Ajusta el modelo por minimos cuadrados ordinarios.

        `cov_type="HC3"` usa errores estandar robustos a heterocedasticidad
        (los coeficientes no cambian, solo sus errores y p-valores).
        """
        self.feature_names_ = list(X.columns)
        Xc = sm.add_constant(X.astype(float), has_constant="add")
        self.results_ = sm.OLS(y.astype(float), Xc).fit(cov_type=self.cov_type)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predice sobre nuevas observaciones (en escala log)."""
        Xc = sm.add_constant(
            X.astype(float)[self.feature_names_], has_constant="add"
        )
        return self.results_.predict(Xc).to_numpy()

    def coefficients(self) -> pd.DataFrame:
        """Coeficientes ordenados por p-valor, con intervalo de confianza."""
        ci = self.results_.conf_int()
        table = pd.DataFrame(
            {
                "coeficiente": self.results_.params,
                "error_std": self.results_.bse,
                "t": self.results_.tvalues,
                "p_valor": self.results_.pvalues,
                "ic_inf": ci[0],
                "ic_sup": ci[1],
            }
        )
        table.index.name = "variable"
        return table.reset_index().sort_values("p_valor", ignore_index=True)

    @staticmethod
    def metrics(y_true, y_pred) -> dict:
        """Metricas en escala log y en la escala original (millones)."""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        # expm1 revierte log1p
        real = np.expm1(y_true)
        pred = np.expm1(y_pred)

        return {
            "R2": r2_score(y_true, y_pred),
            "RMSE_log": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "MAE_log": float(mean_absolute_error(y_true, y_pred)),
            "R2_original": r2_score(real, pred),
            "RMSE_original": float(np.sqrt(mean_squared_error(real, pred))),
            "MAE_original": float(mean_absolute_error(real, pred)),
        }

    def summary(self) -> str:
        """Resumen completo de statsmodels."""
        if self.results_ is None:
            raise ValueError("El modelo no esta ajustado.")
        return str(self.results_.summary())
