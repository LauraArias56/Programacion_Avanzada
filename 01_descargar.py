"""Descarga y explora API datos.gov.co tq63-itzr (generación eléctrica Colombia)."""
import json, requests, pandas as pd, numpy as np

URL = "https://www.datos.gov.co/api/v3/views/tq63-itzr/query.json"
print("Descargando API...")
r = requests.get(URL, timeout=120)
r.raise_for_status()
data = r.json()
print(f"Registros totales: {len(data)}")
df = pd.DataFrame(data)
# Columnas útiles
cols = ["ano","mes","fuente","promedio_mensual_gwh","maximo_gwh","minimo_gwh","generacion_total_gwh","porcentaje_participacion"]
print("Columnas:", df.columns.tolist())
df = df[cols].copy()
for c in ["promedio_mensual_gwh","maximo_gwh","minimo_gwh","generacion_total_gwh","porcentaje_participacion"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype(int)
df["mes"] = pd.to_numeric(df["mes"], errors="coerce").astype(int)
print(df.dtypes)
print("Nulos:\n", df.isnull().sum())
print("Fuentes:", df["fuente"].unique())
print("Rango años:", df["ano"].min(), "-", df["ano"].max())
print(df.describe().round(4).to_string())
df.to_csv("datos_completos.csv", index=False)
print("Guardado datos_completos.csv")
# Verificación relación generacion_total vs promedio (días del mes)
import calendar
df["dias_mes"] = df.apply(lambda x: calendar.monthrange(int(x["ano"]), int(x["mes"]))[1], axis=1)
df["ratio"] = df["generacion_total_gwh"]/df["promedio_mensual_gwh"]
print(df[["ano","mes","fuente","promedio_mensual_gwh","generacion_total_gwh","dias_mes","ratio"]].head(10).to_string())
print("\nRatio describe (debería ~ días del mes):")
print(df["ratio"].describe().round(3).to_string())
