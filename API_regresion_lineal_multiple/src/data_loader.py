"""Carga y perfilado basico del dataset."""

import pandas as pd

from . import config


class DataLoader:
    """Lee el CSV y describe su estructura.

    Ejemplo
    -------
    >>> loader = DataLoader()
    >>> df = loader.load()
    >>> print(loader.profile())
    """

    def __init__(self, path=config.DATA_PATH):
        self.path = path
        self.data = None

    def load(self) -> pd.DataFrame:
        """Carga el CSV y devuelve un DataFrame."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"No se encontro el archivo: {self.path}\n"
                "Descarga el dataset y dejalo en la carpeta data/."
            )
        self.data = pd.read_csv(self.path)
        return self.data

    def profile(self) -> pd.DataFrame:
        """Resumen por columna: tipo, nulos y valores unicos."""
        if self.data is None:
            raise ValueError("Primero hay que llamar a load().")

        return pd.DataFrame(
            {
                "tipo": self.data.dtypes.astype(str),
                "nulos": self.data.isna().sum(),
                "pct_nulos": (self.data.isna().mean() * 100).round(2),
                "unicos": self.data.nunique(),
            }
        )
