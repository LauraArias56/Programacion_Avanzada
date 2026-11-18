"""Entrena el modelo y guarda el artefacto que consume la API.

Uso:
    python train.py
"""

import json
from datetime import datetime, timezone

import numpy as np
from sklearn.model_selection import train_test_split

from src import config
from src.data_loader import DataLoader
from src.model import MultipleLinearRegression
from src.model_bundle import ModelBundle
from src.preprocessing import Preprocessor


def main() -> None:
    print("Entrenando modelo...")

    df = DataLoader().load()
    train_df, test_df = train_test_split(
        df,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
    )

    preprocessor = Preprocessor()
    X_train, y_train = preprocessor.fit_transform(train_df)
    X_test, y_test = preprocessor.transform(test_df)

    model = MultipleLinearRegression(cov_type="HC3").fit(X_train, y_train)

    train_metrics = model.metrics(y_train, model.predict(X_train))
    test_metrics = model.metrics(y_test, model.predict(X_test))

    params = model.results_.params
    bundle = ModelBundle(
        preprocessor=preprocessor,
        coefficients=params.drop("const"),
        intercept=float(params["const"]),
        sigma=float(np.sqrt(model.results_.mse_resid)),
        metadata={
            "version": datetime.now(timezone.utc).strftime("%Y%m%d.%H%M%S"),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "target": config.TARGET,
            "target_transform": "log1p",
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "n_features": int(X_train.shape[1]),
            "metrics": {"train": train_metrics, "test": test_metrics},
            "r2_adj_train": float(model.results_.rsquared_adj),
            "reference_levels": preprocessor.reference_levels_,
            "allowed_platforms": sorted(train_df["platform"].dropna().unique().tolist()),
            "allowed_genres": sorted(train_df["genre"].dropna().unique().tolist()),
            "publisher_levels": preprocessor.publisher_levels_,
            "year_range": [
                int(train_df["year"].min()),
                int(train_df["year"].max()),
            ],
            "excluded_columns": config.DROP_COLUMNS,
            "cov_type": model.cov_type,
        },
    )

    path = bundle.save()
    config.METADATA_PATH.write_text(
        json.dumps(bundle.info(), indent=2, ensure_ascii=False, default=float),
        encoding="utf-8",
    )

    print(f"Artefacto: {path}")
    print(f"Metadatos: {config.METADATA_PATH}")
    print(f"R2 test (log): {test_metrics['R2']:.4f}")
    print(f"Predictores: {X_train.shape[1]}")


if __name__ == "__main__":
    main()
