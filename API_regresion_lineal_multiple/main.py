"""Punto de entrada: ejecuta el flujo completo de regresion lineal multiple.

Uso:
    python main.py
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src import config
from src.data_loader import DataLoader
from src.diagnostics import Diagnostics
from src.model import MultipleLinearRegression
from src.preprocessing import Preprocessor
from src.report import Report


def main() -> None:
    report = Report(config.OUTPUT_DIR, config.FIGURES_DIR)
    lines = []

    def log(text: str = "") -> None:
        print(text)
        lines.append(text)

    # ---------------------------------------------------------- 1. carga
    log("=" * 70)
    log("1. CARGA DE DATOS")
    log("=" * 70)

    loader = DataLoader()
    df = loader.load()
    log(f"Filas: {len(df):,} | Columnas: {df.shape[1]}")
    log("")
    log(loader.profile().to_string())

    # ---------------------------------------------------------- 2. split
    log("\n" + "=" * 70)
    log("2. DIVISION TRAIN / TEST")
    log("=" * 70)

    train_df, test_df = train_test_split(
        df,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
    )
    log(f"Train: {len(train_df):,} filas | Test: {len(test_df):,} filas")

    # ---------------------------------------------------- 3. preproceso
    log("\n" + "=" * 70)
    log("3. PREPROCESAMIENTO")
    log("=" * 70)

    preprocessor = Preprocessor()
    X_train, y_train = preprocessor.fit_transform(train_df)
    X_test, y_test = preprocessor.transform(test_df)

    log(f"Predictores generados: {X_train.shape[1]}")
    log(f"Variable objetivo: log1p({config.TARGET})")
    log("Columnas excluidas: " + ", ".join(config.DROP_COLUMNS))
    log("Categorias de referencia: " + ", ".join(
        f"{k}={v}" for k, v in preprocessor.reference_levels_.items()
    ))

    # --------------------------------------------------------- 4. modelo
    log("\n" + "=" * 70)
    log("4. AJUSTE DEL MODELO (OLS)")
    log("=" * 70)

    model = MultipleLinearRegression(cov_type="HC3").fit(X_train, y_train)

    train_metrics = model.metrics(y_train, model.predict(X_train))
    test_metrics = model.metrics(y_test, model.predict(X_test))

    metrics_table = pd.DataFrame(
        {"metrica": list(train_metrics.keys()),
         "train": list(train_metrics.values()),
         "test": list(test_metrics.values())}
    )
    log("\nMetricas")
    log("-" * 8)
    log(metrics_table.round(4).to_string(index=False))

    log("\nBondad de ajuste (train)")
    log("-" * 23)
    log(f"R2          : {model.results_.rsquared:.4f}")
    log(f"R2 ajustado : {model.results_.rsquared_adj:.4f}")
    log(f"F           : {model.results_.fvalue:.2f} (p = {model.results_.f_pvalue:.2e})")
    log(f"AIC         : {model.results_.aic:.2f}")
    log(f"BIC         : {model.results_.bic:.2f}")

    # ------------------------------------------------ 5. interpretacion
    log("\n" + "=" * 70)
    log("5. COEFICIENTES (10 mas significativos)")
    log("=" * 70)

    coefs = model.coefficients()
    log("")
    log(coefs.head(10).round(4).to_string(index=False))
    log("\nNota: la variable objetivo esta en log1p, asi que un coeficiente b")
    log("multiplica las ventas por exp(b) manteniendo el resto constante.")
    log("Cada dummy se interpreta frente a su categoria de referencia.")
    log("Errores estandar robustos HC3 (validos aunque haya heterocedasticidad).")

    # ------------------------------------------- 5b. especificaciones
    log("\n" + "=" * 70)
    log("5b. COMPARACION DE ESPECIFICACIONES")
    log("=" * 70)

    platform_cols = [c for c in X_train.columns if c.startswith("platform_")]
    specs = {
        "completo": X_train,
        "sin year": X_train.drop(columns=["year"]),
        "sin platform": X_train.drop(columns=platform_cols),
    }

    rows = []
    for name, Xs in specs.items():
        m = MultipleLinearRegression().fit(Xs, y_train)
        test_scores = m.metrics(y_test, m.predict(X_test))
        rows.append(
            {
                "especificacion": name,
                "predictores": Xs.shape[1],
                "R2_train": m.results_.rsquared,
                "R2_test": test_scores["R2"],
                "RMSE_test_log": test_scores["RMSE_log"],
                "VIF_max": Diagnostics(m.results_, Xs).vif()["VIF"].max(),
            }
        )

    comparison = pd.DataFrame(rows)
    log("")
    log(comparison.round(4).to_string(index=False))
    log("\nNota: 'sin year' y 'sin platform' compiten porque ambas codifican la epoca.")
    log("year y platform comparten informacion (cada plataforma vive en una epoca")
    log("concreta), y por eso year es el predictor con mayor VIF.")

    # ----------------------------------------------------- 6. supuestos
    log("\n" + "=" * 70)
    log("6. DIAGNOSTICO DE SUPUESTOS")
    log("=" * 70)

    diagnostics = Diagnostics(model.results_, X_train)

    vif = diagnostics.vif()
    log(Report.dataframe_to_text("VIF (multicolinealidad; >10 es problematico)",
                                 vif, max_rows=10))

    tests = diagnostics.tests()
    log(Report.dataframe_to_text("Contrastes", tests))
    log("Lectura: la heterocedasticidad y la no normalidad son esperables con ventas")
    log("tan asimetricas. Con n grande y errores HC3 la inferencia sigue siendo valida.")

    influential = diagnostics.influential_points()
    log(f"Observaciones influyentes (Cook > 4/n): {len(influential):,} "
        f"de {diagnostics.n:,} ({len(influential) / diagnostics.n:.2%})")

    # ------------------------------------------------------ 7. graficos
    log("\n" + "=" * 70)
    log("7. GRAFICOS")
    log("=" * 70)

    diagnostics.plot_residuals(config.FIGURES_DIR / "residuos_vs_ajustados.png")
    diagnostics.plot_qq(config.FIGURES_DIR / "qq_residuos.png")
    diagnostics.plot_cooks(config.FIGURES_DIR / "distancia_cook.png")
    log(f"Guardados en: {config.FIGURES_DIR}")

    # ------------------------------------------------------ 8. reporte
    log("\n" + "=" * 70)
    log("8. GUARDANDO RESULTADOS")
    log("=" * 70)

    report.save_table("metricas.csv", metrics_table)
    report.save_table("comparacion_especificaciones.csv", comparison)
    report.save_table("coeficientes.csv", coefs.reset_index())
    report.save_table("vif.csv", vif)
    report.save_table("contrastes.csv", tests)
    report.save_table("observaciones_influyentes.csv", influential)

    lines.append("\n" + "=" * 70)
    lines.append("RESUMEN OLS (statsmodels)")
    lines.append("=" * 70)
    lines.append(model.summary())

    path = report.save_text("informe.txt", "\n".join(lines))
    log(f"Informe completo: {path}")
    log(f"Salida de statsmodels incluida al final de informe.txt")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
