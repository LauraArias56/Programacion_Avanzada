"""
Regresión Lineal Múltiple - Predicción anual de producción eléctrica por fuente
y su correlación (Colombia, fuente: datos.gov.co)

Datos: https://www.datos.gov.co/api/v3/views/tq63-itzr/query.json
       (generación eléctrica por fuente: promedio, máximo y mínimo mensual en GWh)

Modelo (mínimos cuadrados ordinarios, NumPy puro, sin sklearn):
    Y = b0 + b1·X1 + b2·X2

    Y  = producción anual total de la fuente en el año (GWh)      [suma de generacion_total_gwh]
    X1 = promedio mensual medio de la fuente en el año (GWh)      [media de promedio_mensual_gwh]
    X2 = máximo mensual de la fuente registrado en el año (GWh)   [máx de maximo_gwh]

El script:
  1. Carga los datos (datos_completos.csv o los descarga de la API).
  2. Agrega a nivel año × fuente (solo años con 12 meses).
  3. Ajusta la RLM por ecuación normal.
  4. Evalúa en entrenamiento y en una prueba temporal (últimos años con datos).
  5. Proyecta X1 y X2 a años futuros por tendencia lineal y predice Y.
  6. Muestra las predicciones anuales por fuente (prueba y futuros) y la correlación.
  7. Guarda figuras y predicciones_futuras.csv.
"""
import os
import numpy as np
import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV_DATOS = "datos_completos.csv"
CSV_FUTUROS = "predicciones_futuras.csv"
URL_API = "https://www.datos.gov.co/api/v3/views/tq63-itzr/query.json"
COLUMNAS = ["ano", "mes", "fuente",
            "promedio_mensual_gwh", "maximo_gwh", "minimo_gwh", "generacion_total_gwh"]
ANOS_FUTUROS = 3  # cuántos años más allá del último disponible se proyectan


def cargar_datos():
    if os.path.exists(CSV_DATOS):
        df = pd.read_csv(CSV_DATOS)
        print(f"Datos cargados de {CSV_DATOS}: {len(df)} filas")
    else:
        print("Descargando datos de datos.gov.co ...")
        r = requests.get(URL_API, timeout=180)
        r.raise_for_status()
        df = pd.DataFrame(r.json())[COLUMNAS].copy()
        df.to_csv(CSV_DATOS, index=False)
        print(f"Descargados y guardados {len(df)} registros en {CSV_DATOS}")
    NUMERICAS = ["promedio_mensual_gwh", "maximo_gwh", "minimo_gwh", "generacion_total_gwh"]
    for c in NUMERICAS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
    df = df.dropna(subset=["ano", "mes", "fuente"] + NUMERICAS)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["fuente"] = df["fuente"].astype(str).str.strip().str.upper()
    return df


def datos_anuales_por_fuente(df):
    g = (df.groupby(["ano", "fuente"])
           .agg(Y=("generacion_total_gwh", "sum"),
                X1=("promedio_mensual_gwh", "mean"),
                X2=("maximo_gwh", "max"),
                meses=("mes", "count"))
           .reset_index())
    g = g[g["meses"] == 12].copy()   # solo años completos
    return g.drop(columns="meses").reset_index(drop=True)


def ajustar_rlm(X, y):
    """Theta por ecuación normal: b = (X'X)^-1 X'y (resuelto sin inversa explícita)."""
    Xd = np.column_stack([np.ones(len(X)), X])
    theta = np.linalg.solve(Xd.T @ Xd, Xd.T @ y)
    return theta, Xd @ theta


def metricas(y, yhat):
    e = y - yhat
    m = len(y)
    sse = float(np.sum(e ** 2))
    mse = sse / m
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(e)))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - sse / sst if sst > 0 else np.nan
    r2aj = 1 - (1 - r2) * (m - 1) / (m - 3) if m > 3 else np.nan
    return {"SSE": sse, "MSE": mse, "RMSE": rmse, "MAE": mae, "R2": r2, "R2_aj": r2aj}


def proyectar_futuros(anual, fuentes, anos_futuros):
    """Proyecta X1 y X2 para cada fuente y años futuros por tendencia lineal vs año."""
    filas = []
    for fuente in fuentes:
        sub = anual[anual["fuente"] == fuente].sort_values("ano")
        if len(sub) < 2:
            continue
        anos = sub["ano"].to_numpy(float)
        x1 = sub["X1"].to_numpy(float)
        x2 = sub["X2"].to_numpy(float)
        coef1 = np.polyfit(anos, x1, 1)
        coef2 = np.polyfit(anos, x2, 1)
        for a in anos_futuros:
            filas.append({
                "ano": int(a),
                "fuente": fuente,
                "X1_proj": float(np.polyval(coef1, a)),
                "X2_proj": float(np.polyval(coef2, a)),
            })
    return pd.DataFrame(filas)


def predecir_futuros(theta, df_futuros):
    Xf = df_futuros[["X1_proj", "X2_proj"]].to_numpy(float)
    Xd = np.column_stack([np.ones(len(Xf)), Xf])
    df_futuros = df_futuros.copy()
    df_futuros["Y_predicho_GWh"] = Xd @ theta
    return df_futuros


def main():
    df = cargar_datos()
    print("\nFuentes:", df["fuente"].nunique(),
          "| Rango de años:", int(df["ano"].min()), "-", int(df["ano"].max()))

    anual = datos_anuales_por_fuente(df)
    print(f"Observaciones año×fuente (años completos, 12 meses): {len(anual)}")

    # Solo fuentes con al menos 8 años de historia, para que el modelo sea estable
    fuentes_validas = anual["fuente"].value_counts()
    fuentes_validas = fuentes_validas[fuentes_validas >= 8].index.tolist()
    anual = anual[anual["fuente"].isin(fuentes_validas)].copy()
    print(f"Filtro: fuentes con >= 8 años -> {len(fuentes_validas)} fuentes: {fuentes_validas}")
    print(f"Observaciones finales: {len(anual)}")

    # División temporal: entrenamiento con años anteriores, prueba con los últimos 4 años
    anos = sorted(anual["ano"].unique())
    corte = anos[-4] if len(anos) >= 4 else anos[int(len(anos) * 0.7)]
    train = anual[anual["ano"] <= corte].copy()
    test = anual[anual["ano"] > corte].copy()
    print(f"\nEntrenamiento: años <= {corte}  ({len(train)} observaciones)")
    print(f"Prueba (años recientes sin usar en entrenamiento): años > {corte}  ({len(test)} observaciones)")

    Xtr = train[["X1", "X2"]].to_numpy(float)
    ytr = train["Y"].to_numpy(float)
    Xte = test[["X1", "X2"]].to_numpy(float)
    yte = test["Y"].to_numpy(float)

    theta, ytr_hat = ajustar_rlm(Xtr, ytr)
    Xd_te = np.column_stack([np.ones(len(Xte)), Xte])
    yte_hat = Xd_te @ theta

    b0, b1, b2 = theta
    print("\n" + "=" * 66)
    print("REGRESIÓN LINEAL MÚLTIPLE (ecuación normal, mínimos cuadrados)")
    print("=" * 66)
    print(f"Ecuación ajustada:  Y = {b0:.4f} + {b1:.6f}·X1 + {b2:.6f}·X2")
    print("  Y  = producción anual total por fuente (GWh/año)")
    print("  X1 = promedio mensual medio anual de la fuente (GWh)")
    print("  X2 = máximo mensual anual de la fuente (GWh)")
    print(f"  Lectura: cada GWh extra de promedio mensual medio añade {b1:.4f} GWh/año;")
    print(f"           cada GWh extra de pico mensual anual añade {b2:.4f} GWh/año.")

    mtr = metricas(ytr, ytr_hat)
    mte = metricas(yte, yte_hat) if len(yte) > 0 else None
    print("\nMétricas ENTRENAMIENTO :", {k: round(v, 4) for k, v in mtr.items()})
    if mte:
        print("Métricas PRUEBA        :", {k: round(v, 4) for k, v in mte.items()})

    # -------------------- Predicción años futuros --------------------
    ultimo_ano = int(anual["ano"].max())
    anos_futuros = list(range(ultimo_ano + 1, ultimo_ano + 1 + ANOS_FUTUROS))
    print(f"\nAños con datos disponibles: hasta {ultimo_ano}")
    print(f"Años futuros proyectados: {anos_futuros}")

    futuros = proyectar_futuros(anual, fuentes_validas, anos_futuros)
    futuros = predecir_futuros(theta, futuros)
    futuros.to_csv(CSV_FUTUROS, index=False)
    print(f"\nPredicciones futuras guardadas en {CSV_FUTUROS}")

    print("\n" + "-" * 66)
    print(f"PREDICCIONES A AÑOS FUTUROS (proyección de tendencia, {anos_futuros})")
    print("-" * 66)
    print(futuros[["ano", "fuente", "X1_proj", "X2_proj", "Y_predicho_GWh"]]
          .round(2)
          .sort_values(["ano", "fuente"])
          .to_string(index=False))

    # -------------------- Correlación --------------------
    corr = anual[["X1", "X2", "Y"]].corr(method="pearson")
    print("\n" + "-" * 66)
    print("CORRELACIÓN DE PEARSON (variables del modelo, datos históricos)")
    print("-" * 66)
    print(corr.round(4).to_string())
    r_real_pred = float(np.corrcoef(yte, yte_hat)[0, 1]) if len(yte) > 1 else np.nan
    print(f"\nCorrelación real vs predicho (prueba, años > {corte}): {r_real_pred:.4f}")

    # -------------------- Predicciones anuales por fuente (prueba) --------------------
    pred = test[["ano", "fuente"]].copy()
    pred["Y_real_GWh"] = np.round(yte, 2)
    pred["Y_predicho_GWh"] = np.round(yte_hat, 2)
    pred["error_GWh"] = np.round(yte - yte_hat, 2)
    print("\n" + "-" * 66)
    print("PREDICCIONES ANUALES DE PRODUCCIÓN POR FUENTE (prueba, años recientes)")
    print("-" * 66)
    print(pred.sort_values(["ano", "fuente"]).round(2).to_string(index=False))

    # -------------------- Figuras --------------------
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # 1) Real vs predicho (prueba)
    ax = axes[0, 0]
    ax.scatter(yte, yte_hat, c="#1f3a5f", alpha=0.75, edgecolor="white", linewidth=0.5)
    lo, hi = float(min(yte.min(), yte_hat.min())), float(max(yte.max(), yte_hat.max()))
    ax.plot([lo, hi], [lo, hi], "g--", linewidth=1.5, label="Y = Ypredicho")
    ax.set_xlabel("Real (GWh/año)"); ax.set_ylabel("Predicho (GWh/año)")
    ax.set_title(f"Real vs Predicho - prueba (años > {corte})\n"
                 f"R² = {mte['R2']:.3f}   r = {r_real_pred:.3f}")
    ax.legend(); ax.grid(True, alpha=0.3)

    # 2) Matriz de correlación
    ax = axes[0, 1]
    im = ax.imshow(corr.values, cmap="RdBu", vmin=-1, vmax=1)
    etiquetas = ["X1 promedio mensual medio", "X2 máximo mensual", "Y producción anual"]
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(etiquetas, rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(etiquetas, fontsize=8)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{corr.values[i, j]:+.2f}", ha="center", va="center",
                    color="white" if abs(corr.values[i, j]) > 0.5 else "black",
                    fontsize=10, fontweight="bold")
    ax.set_title("Matriz de correlación de Pearson")
    fig.colorbar(im, ax=ax, fraction=0.046, label="Correlación")

    # 3) Predicciones futuras por fuente (último año futuro)
    ax = axes[1, 0]
    ano_mas_lejos = anos_futuros[-1]
    sub = futuros[futuros["ano"] == ano_mas_lejos].sort_values("Y_predicho_GWh", ascending=False)
    xpos = np.arange(len(sub))
    ax.bar(xpos, sub["Y_predicho_GWh"], color="#f2c14e", alpha=0.9,
           edgecolor="#b08a1e", label=f"Predicho {ano_mas_lejos}")
    ax.set_xticks(xpos); ax.set_xticklabels(sub["fuente"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("GWh/año")
    ax.set_title(f"Producción anual predicha por fuente - {ano_mas_lejos}")
    ax.legend(); ax.grid(True, alpha=0.3, axis="y")

    # 4) Evolución de la predicción futura para las 3 principales fuentes
    ax = axes[1, 1]
    top3 = (futuros.groupby("fuente")["Y_predicho_GWh"].mean()
              .sort_values(ascending=False).head(3).index.tolist())
    for fuente in top3:
        s = futuros[futuros["fuente"] == fuente].sort_values("ano")
        ax.plot(s["ano"], s["Y_predicho_GWh"], marker="o", label=fuente)
    ax.set_xlabel("Año"); ax.set_ylabel("GWh/año")
    ax.set_title("Tendencia de predicción futura (top 3 fuentes)")
    ax.legend(); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig("fig_predicciones_anuales.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\nFiguras guardadas: fig_predicciones_anuales.png (incluye matriz de correlación y futuros)")
    print("\nFIN DEL ANÁLISIS")


if __name__ == "__main__":
    main()
