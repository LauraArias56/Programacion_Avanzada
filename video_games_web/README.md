# Video Games Web

Aplicacion Flask con frontend Jinja2 + Bootstrap que consume dos APIs FastAPI:
la prediccion de ventas de videojuegos y un clasificador de imagenes CIFAR-10
con transfer learning. Guarda ambos historiales en PostgreSQL y registra logs
estructurados y auditoria de acciones.

La API de regresion original vive en `../API_regresion_lineal_multiple` y **no se
modifica**: este proyecto la consume por HTTP. El modulo de vision vive en
`../vision_api` y se documenta en su propio README.

## Arquitectura

```
Navegador (formulario o camara)
   |
   v
Flask (webapp :5000)  --httpx-->  FastAPI regresion (api :8000)  -->  modelo joblib
   |                --httpx-->  FastAPI vision (vision :8100)  -->  MobileNetV3
   |
   +--> PostgreSQL (:5432): usuarios, historial, auditoria, vision_predictions
   +--> logs/app.log, logs/error.log y stdout
```

## Funcionalidad

- Registro, login y logout con sesiones (Flask-Login) y contrasenas hasheadas.
- Formulario de prediccion con plataformas/generos validados por la API.
- Resultado con ventas estimadas, intervalo 95 %, warnings y version del modelo.
- Historial paginado y filtrable por plataforma, genero y ano.
- Exportacion del historial a CSV.
- Pagina `/vision`: captura desde camara o subida de imagen JPG/PNG/WebP.
- Clasificacion CIFAR-10 con confianza y top 3 servida por `../vision_api`.
- Historial paginado de clasificaciones filtrable por clase.
- Visor de auditoria para administradores.
- Logs JSON con `request_id`, rotacion y redaccion de datos sensibles.
- Auditoria persistente en PostgreSQL.

## Requisitos

- Docker y Docker Compose (recomendado).
- Alternativa local: Python 3.12+, PostgreSQL 16 y la API FastAPI arrancada.

## Arranque rapido con Docker Compose

```bash
cd video_games_web
cp .env.example .env        # en PowerShell: Copy-Item .env.example .env
# edita .env y cambia SECRET_KEY y POSTGRES_PASSWORD
docker compose up --build
```

Servicios:

| Servicio | URL |
|---|---|
| Webapp Flask | <http://localhost:5000> |
| API de regresion | <http://localhost:8000> |
| Swagger de regresion | <http://localhost:8000/docs> |
| Vision API | <http://localhost:8100> |
| Swagger de vision | <http://localhost:8100/docs> |
| PostgreSQL | `localhost:5432` |

El contenedor `webapp` aplica las migraciones (`flask db upgrade`) antes de
arrancar gunicorn. El contenedor `api` se construye con el Dockerfile existente
de `../API_regresion_lineal_multiple`; `vision` se construye desde
`../vision_api` e incluye el checkpoint `artifacts/model.pt`.

La camara del navegador requiere `localhost` o HTTPS. En Docker Compose la web
queda en `http://localhost:5000`, por lo que el permiso de camara funciona sin
configuracion adicional.

Para crear un administrador:

```bash
docker compose exec webapp flask create-admin
```

## Desarrollo local (sin Docker)

1. Instala dependencias:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

2. Arranca las dos APIs en otras terminales:

   ```bash
   cd ../API_regresion_lineal_multiple
   python -m uvicorn api.main:app --port 8000
   ```

   ```bash
   cd ../vision_api
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-train.txt
   python -m uvicorn api.main:app --port 8100
   ```

   La Vision API necesita el checkpoint `vision_api/artifacts/model.pt`. Si no
   existe, entrena primero con `python train.py` (ver README de `vision_api`).

3. Crea el `.env` y ajusta `DATABASE_URL` a tu PostgreSQL local (o deja el
   SQLite por defecto para pruebas):

   ```bash
   Copy-Item .env.example .env
   ```

4. Aplica migraciones y arranca Flask:

   ```bash
   python -m flask --app wsgi db upgrade
   python wsgi.py
   ```

La app queda en <http://127.0.0.1:5000>.

## Variables de entorno

| Variable | Descripcion | Default |
|---|---|---|
| `SECRET_KEY` | Clave de sesiones y CSRF | valor de desarrollo |
| `DATABASE_URL` | URL SQLAlchemy (PostgreSQL o SQLite) | `sqlite:///local.db` |
| `API_BASE_URL` | URL base de la API FastAPI | `http://127.0.0.1:8000` |
| `API_TIMEOUT` | Timeout de httpx en segundos | `10` |
| `API_RETRIES` | Reintentos ante error de red/5xx | `3` |
| `MODEL_INFO_TTL` | Cache de `/model` en segundos | `300` |
| `VISION_API_BASE_URL` | URL base de la Vision API | `http://127.0.0.1:8100` |
| `VISION_API_TIMEOUT` | Timeout de la Vision API en segundos | `20` |
| `VISION_API_RETRIES` | Reintentos de la Vision API | `2` |
| `VISION_MODEL_INFO_TTL` | Cache de `/model` de vision en segundos | `300` |
| `VISION_MAX_UPLOAD_MB` | Tamano maximo de imagen | `8` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `LOG_DIR` | Directorio de logs | `logs` |
| `SESSION_COOKIE_SECURE` | Cookies solo por HTTPS | `0` |
| `RATELIMIT_ENABLED` | Limite de intentos de login/registro | `1` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credenciales de Compose | ver `.env.example` |

## Logs

Se escriben simultaneamente a stdout y a archivos rotativos:

- `logs/app.log`: todos los eventos desde `LOG_LEVEL`.
- `logs/error.log`: solo errores.
- Rotacion: 10 MB por archivo, 5 copias (configurable con `LOG_MAX_BYTES` y
  `LOG_BACKUP_COUNT`).

Cada linea es JSON con `timestamp`, `level`, `logger`, `message`, `request_id`,
`user_id` y campos de contexto (`http_method`, `path`, `status`, `duration_ms`,
`ip`, `action`, etc.). El `request_id` se propaga a la API mediante la cabecera
`X-Request-ID`. Un filtro elimina contrasenas, tokens, cookies y cabeceras
`Authorization` de los mensajes.

Ver logs en vivo:

```bash
docker compose logs -f webapp
```

## Auditoria

La tabla `audit_logs` registra:

- `auth.register`, `auth.login_success`, `auth.login_failed`, `auth.logout`
- `prediction.created`, `prediction.failed`
- `vision.prediction.created`, `vision.prediction_failed`
- `admin.audit_viewed`, `admin.created`

Cada registro incluye usuario, accion, estado, IP, user-agent, `request_id`,
metadatos JSON y error (si aplica). Los administradores pueden consultarla en
`/admin/audit` con filtros por accion, usuario y fechas.

Retencion manual:

```bash
docker compose exec webapp flask audit-prune --days 90
```

## Tests

```bash
python -m pytest -q
```

Cubren autenticacion, prediccion de ventas, vision, historiales, permisos de
administrador, auditoria, redaccion de logs y los clientes HTTP con transportes
simulados.

## Estructura

```
app/
  __init__.py          create_app()
  config.py            Configuracion por variables de entorno
  extensions.py        db, migrate, login, csrf, limiter
  logging_config.py    JSON logs, request_id, rotacion, redaccion
  hooks.py             Logs de requests y contexto
  errors.py            Paginas 403/404/500/503
  cli.py               create-admin, audit-prune
  models/              User, Prediction, AuditLog, VisionPrediction
  services/            ApiClient, VisionApiClient httpx, record_audit
  blueprints/          auth, main, admin, vision
  forms/               WTForms
  templates/           Jinja2 + Bootstrap 5
  static/css/          style.css, vision.css
  static/js/           vision.js (camara, captura y fetch)
migrations/            Alembic
tests/
logs/
Dockerfile
docker-compose.yml
```

## Notas de seguridad

- Cambia `SECRET_KEY` y las credenciales de PostgreSQL en produccion.
- Activa `SESSION_COOKIE_SECURE=1` si sirves la app por HTTPS.
- El login y el registro tienen rate limit (10/min y 5/min).
- Todos los formularios usan CSRF.
- Los logs no deben contener datos sensibles: el filtro de redaccion es una
  defensa adicional, no una excusa para registrar secretos.
