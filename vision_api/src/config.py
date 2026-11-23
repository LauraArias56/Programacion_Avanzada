"""Rutas y parametros compartidos por entrenamiento e inferencia."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", str(BASE_DIR / "artifacts")))
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(ARTIFACTS_DIR / "model.pt")))
CLASSES_PATH = Path(os.getenv("CLASSES_PATH", str(ARTIFACTS_DIR / "classes.json")))
METRICS_PATH = Path(os.getenv("METRICS_PATH", str(ARTIFACTS_DIR / "metrics.json")))
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", str(ARTIFACTS_DIR)))

GAME_ARTIFACTS_DIR = Path(
    os.getenv("GAME_ARTIFACTS_DIR", str(ARTIFACTS_DIR / "game_genres"))
)
GAME_MODEL_PATH = Path(
    os.getenv("GAME_MODEL_PATH", str(GAME_ARTIFACTS_DIR / "model.pt"))
)
GAME_CLASSES_PATH = Path(
    os.getenv("GAME_CLASSES_PATH", str(GAME_ARTIFACTS_DIR / "classes.json"))
)
GAME_METRICS_PATH = Path(
    os.getenv("GAME_METRICS_PATH", str(GAME_ARTIFACTS_DIR / "metrics.json"))
)
GAME_PROFILES_PATH = Path(
    os.getenv("GAME_PROFILES_PATH", str(GAME_ARTIFACTS_DIR / "genre_profiles.json"))
)
GAME_DATA_DIR = Path(os.getenv("GAME_DATA_DIR", str(DATA_DIR / "game_covers")))

IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "160"))
GAME_IMAGE_SIZE = int(os.getenv("GAME_IMAGE_SIZE", "224"))
GAME_EVAL_RESIZE = int(os.getenv("GAME_EVAL_RESIZE", "256"))
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "8"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
