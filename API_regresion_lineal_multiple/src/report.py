"""Salida de resultados a disco (texto y tablas)."""

from pathlib import Path

import pandas as pd


class Report:
    """Guarda el informe en texto plano y las tablas en CSV."""

    def __init__(self, output_dir, figures_dir):
        self.output_dir = Path(output_dir)
        self.figures_dir = Path(figures_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    def save_text(self, filename: str, content: str) -> Path:
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def save_table(self, filename: str, table: pd.DataFrame) -> Path:
        path = self.output_dir / filename
        table.to_csv(path, index=False, encoding="utf-8")
        return path

    @staticmethod
    def dataframe_to_text(title: str, table: pd.DataFrame, max_rows: int = 20) -> str:
        body = table.head(max_rows).to_string(index=False)
        extra = ""
        if len(table) > max_rows:
            extra = f"\n... ({len(table) - max_rows} filas mas)"
        return f"\n{title}\n{'-' * len(title)}\n{body}{extra}\n"
