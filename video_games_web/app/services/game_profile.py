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

GENRE_PROFILES = {
    "Action": {
        "theme": "accion y combate",
        "platform": "PS4",
        "publisher": "Electronic Arts",
    },
    "Adventure": {
        "theme": "aventura y exploracion",
        "platform": "PS4",
        "publisher": "Ubisoft",
    },
    "Fighting": {
        "theme": "combate cuerpo a cuerpo",
        "platform": "PS4",
        "publisher": "Bandai Namco",
    },
    "Platform": {
        "theme": "saltos y plataformas",
        "platform": "Wii",
        "publisher": "Nintendo",
    },
    "Puzzle": {
        "theme": "logica y rompecabezas",
        "platform": "PC",
        "publisher": "Nintendo",
    },
    "Racing": {
        "theme": "carreras y velocidad",
        "platform": "PS4",
        "publisher": "Electronic Arts",
    },
    "Role-Playing": {
        "theme": "rol y narrativa",
        "platform": "PC",
        "publisher": "Bethesda Softworks",
    },
    "Shooter": {
        "theme": "disparos y accion",
        "platform": "PS4",
        "publisher": "Activision",
    },
    "Simulation": {
        "theme": "simulacion y gestion",
        "platform": "PC",
        "publisher": "Ubisoft",
    },
    "Sports": {
        "theme": "deportes y competicion",
        "platform": "PS4",
        "publisher": "Electronic Arts",
    },
    "Strategy": {
        "theme": "estrategia y planificacion",
        "platform": "PC",
        "publisher": "Paradox Interactive",
    },
}


def _allowed(value: str, choices: list[str], fallback: str) -> str:
    if value in choices:
        return value
    if fallback in choices:
        return fallback
    return choices[0] if choices else value


def _finalize_profile(profile: dict, model_info: dict | None = None) -> dict:
    info = model_info or {}
    platforms = list(info.get("allowed_platforms") or [])
    genres = list(info.get("allowed_genres") or [])
    year_range = info.get("year_range") or [1980, 2020]
    try:
        year_min, year_max = int(year_range[0]), int(year_range[1])
    except (TypeError, ValueError, IndexError):
        year_min, year_max = 1980, 2020

    try:
        year = int(profile.get("year", DEFAULT_YEAR))
    except (TypeError, ValueError):
        year = DEFAULT_YEAR
    year = min(max(year, year_min), year_max)

    return {
        "platform": _allowed(
            profile.get("platform", DEFAULT_PLATFORM), platforms, DEFAULT_PLATFORM
        ),
        "genre": _allowed(
            profile.get("genre", DEFAULT_GENRE), genres, DEFAULT_GENRE
        ),
        "publisher": profile.get("publisher", DEFAULT_PUBLISHER),
        "year": year,
        "theme": profile.get("theme", FALLBACK_PROFILE["theme"]),
    }


def _genre_profiles_map(genre_profiles: dict | None) -> dict:
    if not isinstance(genre_profiles, dict):
        return {}
    nested = genre_profiles.get("genres")
    if isinstance(nested, dict):
        return nested
    return {
        key: value
        for key, value in genre_profiles.items()
        if isinstance(value, dict)
    }


def _profile_for_genre(genre: str, genre_profiles: dict | None = None) -> dict:
    profile = dict(GENRE_PROFILES.get(genre, FALLBACK_PROFILE))
    override = _genre_profiles_map(genre_profiles).get(genre)
    if isinstance(override, dict):
        for key in ("theme", "platform", "publisher", "year"):
            if override.get(key) is not None:
                profile[key] = override[key]
    return profile


def infer_game_profile(label: str, model_info: dict | None = None) -> dict:
    """Devuelve plataforma, genero, editorial, año y tema para una clase."""
    profile = dict(PROFILES_BY_LABEL.get(label, FALLBACK_PROFILE))
    return _finalize_profile(profile, model_info)


def infer_game_profile_from_genre(
    genre: str,
    model_info: dict | None = None,
    genre_profiles: dict | None = None,
) -> dict:
    """Construye el perfil de ventas a partir del genero detectado."""
    profile = _profile_for_genre(genre, genre_profiles)
    profile["genre"] = genre
    return _finalize_profile(profile, model_info)


def theme_for_label(label: str) -> str:
    return PROFILES_BY_LABEL.get(label, FALLBACK_PROFILE)["theme"]


def theme_for_genre(genre: str, genre_profiles: dict | None = None) -> str:
    return _profile_for_genre(genre, genre_profiles)["theme"]
