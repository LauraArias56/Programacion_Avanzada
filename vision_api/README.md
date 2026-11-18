# Vision API - CIFAR-10

Microservicio FastAPI que clasifica imagenes en una de las 10 clases de CIFAR-10
usando **transfer learning** con MobileNetV3-Small preentrenado en ImageNet. Es
consumido por la webapp Flask (`../video_games_web`) y puede probarse de forma
independiente con Swagger.

## Modelo y resultados

| Elemento | Valor |
|---|---|
| Arquitectura | MobileNetV3-Small (ImageNet IMAGENET1K_V1) |
| Estrategia | Backbone congelado + cabeza clasificadora entrenada |
| Entrada | RGB 160 x 160, normalizacion ImageNet, tensor NCHW |
| Clases | 10 clases CIFAR-10 |
| Entrenamiento | 20 000 imagenes balanceadas (2 000 por clase) |
| Evaluacion | 4 000 imagenes balanceadas (400 por clase) |
| Accuracy test | **88.63 %** |
| Macro F1 | **88.61 %** |
| Version del modelo | `cifar10-mobilenetv3-20261118.192953` |

Metricas completas en `artifacts/metrics.json`. Figuras generadas durante el
entrenamiento:

- `artifacts/figures/confusion_matrix.png`
- `artifacts/figures/training_curves.png`
- `artifacts/figures/sample_predictions.png`

La matriz de confusion muestra que las confusiones mas frecuentes son
gato/perro y automovil/camion, tipicas de CIFAR-10 a esta resolucion.

## Dataset

Se usa CIFAR-10 mediante `torchvision.datasets.CIFAR10`. La descarga oficial
desde `cs.toronto.edu` puede fallar por DNS o certificados; el script usa por
defecto un mirror verificado de GitHub y permite cambiarlo:

```bash
set CIFAR10_URL=https://otro-mirror/cifar-10-python.tar.gz
python train.py
```

El MD5 esperado del archivo oficial es `c58f30108f718f92721af3b95e74349a`.
Los datos se guardan en `data/` y no se versionan.

## Entrenamiento

```powershell
cd vision_api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-train.txt
python train.py
```

El script:

1. Descarga CIFAR-10 si hace falta.
2. Carga MobileNetV3-Small con pesos ImageNet.
3. Congela el backbone y extrae caracteristicas una sola vez.
4. Entrena la cabeza `Linear(576, 512) -> Hardswish -> Dropout -> Linear(512, 10)`.
5. Evalua en el subconjunto de test y guarda checkpoint, clases, metricas y figuras.

Artefactos generados en `artifacts/`:

```
artifacts/
  model.pt
  classes.json
  metrics.json
  figures/
    confusion_matrix.png
    training_curves.png
    sample_predictions.png
```

## Ejecucion local

```powershell
cd vision_api
.\.venv\Scripts\activate
python -m uvicorn api.main:app --port 8100
```

- API: <http://localhost:8100>
- Swagger: <http://localhost:8100/docs>
- Health: <http://localhost:8100/health>

Variables utiles:

| Variable | Default | Descripcion |
|---|---|---|
| `MODEL_PATH` | `artifacts/model.pt` | Checkpoint |
| `IMAGE_SIZE` | `160` | Resolucion de entrada |
| `MAX_UPLOAD_MB` | `8` | Limite de subida |
| `CIFAR10_URL` | mirror GitHub | Fuente del dataset |

## Endpoints

### `GET /health`

```json
{"status": "ok", "model_version": "cifar10-mobilenetv3-20261118.192953"}
```

### `GET /model`

Devuelve arquitectura, dataset, clases, preprocessing, metricas y disclaimer.

### `POST /predict`

Multipart con el campo `file` y parametro opcional `top_k` (1-10):

```bash
curl.exe -X POST "http://localhost:8100/predict?top_k=3" ^
  -F "file=@foto.jpg;type=image/jpeg"
```

Respuesta:

```json
{
  "prediction": {
    "label": "cat",
    "label_es": "gato",
    "confidence": 0.9123,
    "top_k": [
      {"class_id": 3, "label": "cat", "label_es": "gato", "confidence": 0.9123},
      {"class_id": 5, "label": "dog", "label_es": "perro", "confidence": 0.0412}
    ],
    "latency_ms": 25.4
  },
  "model_version": "cifar10-mobilenetv3-20261118.192953",
  "request_id": "..."
}
```

Formatos aceptados: JPG, PNG y WebP. Errores: `415` formato no soportado,
`400` imagen vacia, `413` imagen demasiado grande, `422` imagen invalida.

## Docker

```bash
docker build -t vision-api .
docker run --rm -p 8100:8100 vision-api
```

El Dockerfile instala PyTorch CPU desde el indice oficial y copia `api/`, `src/`
y `artifacts/` (incluido `model.pt`). En el proyecto completo se levanta con
`docker compose up --build` desde `video_games_web`.

## Tests

```powershell
python -m pytest -q
```

Incluyen endpoints con un servicio simulado y una prueba de humo del modelo
real cuando existe `artifacts/model.pt`.

## Limitaciones

CIFAR-10 contiene imagenes de 32 x 32 de baja resolucion. Las fotos de camara
tienen otra distribucion (fondo, iluminacion, encuadre), por lo que la confianza
debe interpretarse como una demostracion del flujo de vision, no como un
clasificador listo para produccion.
