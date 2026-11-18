"""Verificacion de los supuestos del modelo lineal."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera


class Diagnostics:
    """Contrastes y graficos sobre el modelo ajustado.

    - VIF              -> multicolinealidad
    - Breusch-Pagan    -> homocedasticidad
    - Jarque-Bera      -> normalidad de los residuos
    - Durbin-Watson    -> autocorrelacion
    - Distancia de Cook-> observaciones influyentes
    """

    def __init__(self, results, X: pd.DataFrame):
        self.results = results
        self.X = X
        self.n = int(results.nobs)
        self.k = int(X.shape[1])

    # ------------------------------------------------------------ contrastes
    def vif(self) -> pd.DataFrame:
        """Factor de inflacion de la varianza por predictor."""
        Xc = sm.add_constant(self.X.astype(float), has_constant="add")
        rows = [
            {
                "variable": col,
                "VIF": variance_inflation_factor(Xc.values, i),
            }
            for i, col in enumerate(Xc.columns)
            if col != "const"
        ]
        return pd.DataFrame(rows).sort_values("VIF", ascending=False).reset_index(drop=True)

    def tests(self) -> pd.DataFrame:
        """Contrastes de supuestos con su lectura."""
        resid = np.asarray(self.results.resid, dtype=float)
        exog = np.asarray(self.results.model.exog, dtype=float)

        bp = het_breuschpagan(resid, exog)          # (lm, p, f, p_f)
        jb = jarque_bera(resid)                     # (stat, p, skew, kurtosis)
        dw = durbin_watson(resid)

        return pd.DataFrame(
            [
                {
                    "supuesto": "Homocedasticidad (Breusch-Pagan)",
                    "estadistico": bp[0],
                    "p_valor": bp[1],
                    "veredicto": "OK" if bp[1] > 0.05 else "Se incumple",
                },
                {
                    "supuesto": "Normalidad de residuos (Jarque-Bera)",
                    "estadistico": jb[0],
                    "p_valor": jb[1],
                    "veredicto": "OK" if jb[1] > 0.05 else "Se incumple",
                },
                {
                    "supuesto": "Autocorrelacion (Durbin-Watson)",
                    "estadistico": dw,
                    "p_valor": np.nan,
                    "veredicto": "OK" if 1.5 <= dw <= 2.5 else "Revisar",
                },
            ]
        )

    def influential_points(self, threshold: float = None) -> pd.DataFrame:
        """Observaciones con distancia de Cook alta."""
        threshold = threshold or 4.0 / self.n
        cooks = self.results.get_influence().cooks_distance[0]
        table = pd.DataFrame({"indice": np.arange(self.n), "cook": cooks})
        return (
            table[table["cook"] > threshold]
            .sort_values("cook", ascending=False)
            .reset_index(drop=True)
        )

    # --------------------------------------------------------------- graficos
    def plot_residuals(self, path):
        """Residuos vs valores ajustados."""
        fitted = self.results.fittedvalues
        resid = self.results.resid

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.scatter(fitted, resid, s=8, alpha=0.4, edgecolors="none")
        ax.axhline(0, color="crimson", linestyle="--", linewidth=1)
        ax.set_xlabel("Valores ajustados (log)")
        ax.set_ylabel("Residuos")
        ax.set_title("Residuos vs ajustados")
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)

    def plot_qq(self, path):
        """Grafico Q-Q de los residuos."""
        fig = sm.qqplot(self.results.resid, line="45", fit=True)
        fig.set_size_inches(5.5, 5)
        fig.axes[0].set_title("Q-Q de residuos")
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)

    def plot_cooks(self, path):
        """Distancia de Cook por observacion."""
        cooks = self.results.get_influence().cooks_distance[0]
        threshold = 4.0 / self.n

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.vlines(np.arange(self.n), 0, cooks, linewidth=0.6, color="steelblue")
        ax.axhline(threshold, color="crimson", linestyle="--", linewidth=1,
                   label=f"umbral = 4/n = {threshold:.2e}")
        ax.set_xlabel("Observacion")
        ax.set_ylabel("Distancia de Cook")
        ax.set_title("Observaciones influyentes")
        ax.legend()
        fig.tight_layout()
        fig.savefig(path, dpi=130)
        plt.close(fig)
