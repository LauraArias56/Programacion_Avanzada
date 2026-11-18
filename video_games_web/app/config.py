"""Configuracion central de la aplicacion Flask."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    return f"sqlite:///{(BASE_DIR / 'local.db').as_posix()}"


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    API_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))
    API_RETRIES = int(os.getenv("API_RETRIES", "3"))
    MODEL_INFO_TTL = int(os.getenv("MODEL_INFO_TTL", "300"))

    VISION_API_BASE_URL = os.getenv(
        "VISION_API_BASE_URL", "http://127.0.0.1:8100"
    ).rstrip("/")
    VISION_API_TIMEOUT = float(os.getenv("VISION_API_TIMEOUT", "20"))
    VISION_API_RETRIES = int(os.getenv("VISION_API_RETRIES", "2"))
    VISION_MODEL_INFO_TTL = int(os.getenv("VISION_MODEL_INFO_TTL", "300"))
    VISION_MAX_UPLOAD_MB = int(os.getenv("VISION_MAX_UPLOAD_MB", "8"))
    MAX_CONTENT_LENGTH = (VISION_MAX_UPLOAD_MB + 4) * 1024 * 1024
    VISION_HISTORY_PAGE_SIZE = int(os.getenv("VISION_HISTORY_PAGE_SIZE", "12"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_TIME_LIMIT = None

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = _env_bool("RATELIMIT_ENABLED", "1")

    HISTORY_PAGE_SIZE = int(os.getenv("HISTORY_PAGE_SIZE", "15"))
    AUDIT_PAGE_SIZE = int(os.getenv("AUDIT_PAGE_SIZE", "25"))
