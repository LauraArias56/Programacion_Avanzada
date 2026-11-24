"""Perfil de videojuego inferido a partir del tema visual detectado.

CIFAR-10 no identifica titulos ni editoriales. Estas reglas traducen la clase
visual dominante a un perfil aproximado que el modelo de ventas puede consumir.
El usuario puede corregir el perfil desde la interfaz antes de recalcular.
"""

from __future__ import annotations

DEFAULT_PLATFORM = "PS4"
DEFAULT_GENRE = "Action"
DEFAULT_PUBLISHER = "Other"
DEFAULT_YEAR = 2015

PROFILES_BY_LABEL = {
    "airplane": {
        "theme": "aviacion y combate aereo",
        "platform": "PS4",
        "genre": "Simulation",
        "publisher": "Ubisoft",
    },
    "automobile": {
        "theme": "coches y carreras",
        "platform": "PS4",
        "genre": "Racing",
        "publisher": "Electronic Arts",
    },
    "bird": {
        "theme": "naturaleza y exploracion",
        "platform": "Wii",
        "genre": "Adventure",
        "publisher": "Nintendo",
    },
    "cat": {
        "theme": "mascotas y familia",
        "platform": "Wii",
        "genre": "Misc",
        "publisher": "Nintendo",
    },
    "deer": {
        "theme": "naturaleza y aventura",
        "platform": "Wii",
        "genre": "Adventure",
        "publisher": "Nintendo",
    },
    "dog": {
        "theme": "mascotas y familia",
        "platform": "Wii",
        "genre": "Misc",
        "publisher": "Nintendo",
    },
    "frog": {
        "theme": "personajes y plataformas",
        "platform": "Wii",
        "genre": "Platform",
        "publisher": "Nintendo",
    },
    "horse": {
        "theme": "deportes y equitacion",
        "platform": "PS4",
        "genre": "Sports",
        "publisher": "Electronic Arts",
    },
    "ship": {
        "theme": "estrategia naval",
        "platform": "PC",
        "genre": "Strategy",
        "publisher": "Ubisoft",
    },
    "truck": {
        "theme": "simulacion de vehiculos",
        "platform": "PS4",
        "genre": "Simulation",
        "publisher": "Electronic Arts",
    },
}

FALLBACK_PROFILE = {
    "theme": "imagen de videojuego",
    "platform": DEFAULT_PLATFORM,
    "genre": DEFAULT_GENRE,
    "publisher": DEFAULT_PUBLISHER,
}


def _allowed(value: str, choices: list[str], fallback: str) -> str:
    if value in choices:
        return value
    if fallback in choices:
        return fallback
    return choices[0] if choices else value


def infer_game_profile(label: str, model_info: dict | None = None) -> dict:
    """Devuelve plataforma, genero, editorial, año y tema para una clase."""
    profile = PROFILES_BY_LABEL.get(label, FALLBACK_PROFILE)
    info = model_info or {}

    platforms = list(info.get("allowed_platforms") or [])
    genres = list(info.get("allowed_genres") or [])
    year_range = info.get("year_range") or [1980, 2020]
    try:
        year_min, year_max = int(year_range[0]), int(year_range[1])
    except (TypeError, ValueError, IndexError):
        year_min, year_max = 1980, 2020

    year = min(max(DEFAULT_YEAR, year_min), year_max)

    return {
        "platform": _allowed(profile.get("platform", DEFAULT_PLATFORM), platforms, DEFAULT_PLATFORM),
        "genre": _allowed(profile.get("genre", DEFAULT_GENRE), genres, DEFAULT_GENRE),
        "publisher": profile.get("publisher", DEFAULT_PUBLISHER),
        "year": year,
        "theme": profile.get("theme", FALLBACK_PROFILE["theme"]),
    }


def theme_for_label(label: str) -> str:
    return PROFILES_BY_LABEL.get(label, FALLBACK_PROFILE)["theme"]
