# Regresión lineal múltiple — Video Games Sales

Implementación con POO sobre el dataset
[Video Games Sales](https://www.kaggle.com/datasets/ulrikthygepedersen/video-games-sales).

## Objetivo

Predecir `global_sales` (millones de unidades) a partir de:

- `year` (numérica)
- `platform`, `genre`, `publisher` (categóricas → dummies)

## Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Se excluye `rank` | Es el orden por ventas: fuga de información |
| Se excluye `name` | Identificador de alta cardinalidad |
| Se excluyen las 4 ventas regionales | Suman exactamente `global_sales` → colinealidad perfecta |
| `Y = log1p(global_sales)` | Las ventas están muy sesgadas; el log estabiliza la varianza |
| `publisher` agrupado en top 30 + "Other" | ~579 niveles generarían demasiadas dummies |
| Referencia = categoría más frecuente | Evita la trampa de las dummies y que la referencia sea una categoría rara |
| `year` centrado en su media | El intercepto deja de ser una extrapolación a `year = 0` |
| Errores estándar HC3 | Breusch-Pagan confirma heterocedasticidad; los p-valores quedan válidos |

## Estructura

```
train.py                 Entrena y guarda artifacts/model.joblib
main.py                  Analisis completo + informe (EDA, supuestos, graficos)
api/
  main.py                Aplicacion FastAPI
  service.py             ModelService: validacion + prediccion
  schemas.py             Contratos Pydantic (entrada/salida)
src/
  config.py              Rutas y parametros
  data_loader.py         DataLoader: carga y perfilado
  preprocessing.py       Preprocessor: limpieza, imputacion, dummies
  model.py               MultipleLinearRegression: OLS + metricas
  model_bundle.py        ModelBundle: artefacto serializable
  diagnostics.py         Diagnostics: VIF, BP, JB, DW, Cook, graficos
  report.py              Report: guarda informe y tablas
tests/
  test_api.py            Pruebas de la API con TestClient
examples/
  client.py              Ejemplo de consumo desde otro sistema
data/
  video_games_sales.csv
artifacts/
  model.joblib           Modelo entrenado (lo genera train.py)
  metadata.json          Metadatos legibles (version, metricas, categorias)
outputs/
  informe.txt
  metricas.csv, coeficientes.csv, vif.csv, contrastes.csv, ...
  figures/*.png
```

## Instalación

```bash
python -m pip install -r requirements.txt
```

## Entrenar el modelo

```bash
python train.py
```

Genera `artifacts/model.joblib` y `artifacts/metadata.json`. Hay que repetirlo
cada vez que cambien los datos o la configuración.

## Uso como API

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Documentación interactiva (Swagger): <http://localhost:8000/docs>

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio y versión del modelo |
| GET | `/model` | Metadatos: métricas, categorías válidas, rango de años |
| POST | `/predict` | Predice un videojuego |
| POST | `/predict/batch` | Predice hasta 1000 videojuegos |

### Ejemplo

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"platform":"PS4","genre":"Action","publisher":"Activision","year":2015}'
```

```json
{
  "prediction": {
    "predicted_sales_millions": 0.6827,
    "predicted_log_sales": 0.5204,
    "interval_95_millions": [0.0, 2.2618],
    "warnings": []
  },
  "model_version": "20261111.194437"
}
```

Reglas de validación:

- `platform` y `genre` deben existir en el dataset → si no, `422` con la lista de valores válidos.
- `publisher` desconocida → se agrupa como `Other` y se devuelve un `warning`.
- `year` fuera del rango de entrenamiento → se predice igual, pero se avisa que es extrapolación.

### Cliente de ejemplo

```bash
python examples/client.py
```

### Pruebas

```bash
python -m pytest tests -q
```

## Resultados obtenidos

| Métrica | Train | Test |
|---|---|---|
| R² (log) | 0.2651 | 0.2465 |
| RMSE (log) | 0.3368 | 0.3546 |
| MAE (log) | 0.2201 | 0.2255 |
| R² (millones) | 0.1183 | 0.0591 |

- **Multicolinealidad:** VIF máximo 7.5 (`year`), por debajo del umbral de 10.
- **Heterocedasticidad:** se incumple (Breusch-Pagan p ≈ 0), corregida con HC3.
- **Normalidad:** se incumple (Jarque-Bera p ≈ 0), esperable por la asimetría.
- **Autocorrelación:** Durbin-Watson = 2.00, sin problema.
- **Influyentes:** 622 observaciones (4,7%) superan Cook > 4/n.

Categorías de referencia: `platform = PS2`, `genre = Action`, `publisher = Other`.
Los coeficientes de las dummies se leen frente a esas categorías.

## Interpretación de resultados

- **R²**: proporción de varianza de `log1p(global_sales)` explicada.
- **Coeficientes**: al estar la Y en log, `exp(b)` es el factor multiplicativo
  sobre las ventas.
- **VIF > 10**: multicolinealidad problemática.
- **Breusch-Pagan p < 0.05**: heterocedasticidad.
- **Jarque-Bera p < 0.05**: residuos no normales (esperable con datos tan
  asimétricos; con n grande el estimador sigue siendo consistente).
- **Durbin-Watson**: valores entre 1.5 y 2.5 se consideran aceptables.

## Limitaciones

El dataset no contiene presupuesto de marketing, calidad ni franquicia, por lo
que el R² será moderado (≈0.2–0.4). Sirve para demostrar el método y validar
supuestos, no para pronosticar ventas con precisión. Además, un mismo juego
aparece repetido en varias plataformas, lo que rompe la independencia de las
observaciones.
