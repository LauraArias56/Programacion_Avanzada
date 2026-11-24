"""Generos de videojuego y mapeo desde las etiquetas de IGDB.

El modelo de generos predice las mismas etiquetas que consume la API de
regresion de ventas, excepto ``Misc``. ``Misc`` se reserva como fallback para
cuando la confianza del clasificador es baja.
"""

GAME_GENRES = [
    {"id": 0, "label": "Action", "label_es": "accion", "theme": "accion y combate"},
    {
        "id": 1,
        "label": "Adventure",
        "label_es": "aventura",
        "theme": "aventura y exploracion",
    },
    {
        "id": 2,
        "label": "Fighting",
        "label_es": "lucha",
        "theme": "combates cuerpo a cuerpo",
    },
    {
        "id": 3,
        "label": "Platform",
        "label_es": "plataformas",
        "theme": "plataformas y saltos",
    },
    {"id": 4, "label": "Puzzle", "label_es": "puzles", "theme": "logica y puzles"},
    {
        "id": 5,
        "label": "Racing",
        "label_es": "carreras",
        "theme": "coches y carreras",
    },
    {
        "id": 6,
        "label": "Role-Playing",
        "label_es": "rol",
        "theme": "rol y narrativa",
    },
    {
        "id": 7,
        "label": "Shooter",
        "label_es": "disparos",
        "theme": "disparos y accion",
    },
    {
        "id": 8,
        "label": "Simulation",
        "label_es": "simulacion",
        "theme": "simulacion",
    },
    {"id": 9, "label": "Sports", "label_es": "deportes", "theme": "deportes"},
    {
        "id": 10,
        "label": "Strategy",
        "label_es": "estrategia",
        "theme": "estrategia y gestion",
    },
]

GAME_LABELS = [item["label"] for item in GAME_GENRES]
GAME_LABELS_ES = [item["label_es"] for item in GAME_GENRES]
GAME_GENRE_BY_LABEL = {item["label"]: item for item in GAME_GENRES}

MISC_GENRE = {
    "id": 11,
    "label": "Misc",
    "label_es": "mixto",
    "theme": "genero mixto",
}

SALES_GENRES = GAME_LABELS + [MISC_GENRE["label"]]

IGDB_GENRE_TO_SALES = {
    "action": "Action",
    "adventure": "Adventure",
    "point-and-click": "Adventure",
    "visual novel": "Adventure",
    "fighting": "Fighting",
    "hack and slash/beat 'em up": "Fighting",
    "platform": "Platform",
    "puzzle": "Puzzle",
    "card & board game": "Puzzle",
    "racing": "Racing",
    "role-playing (rpg)": "Role-Playing",
    "shooter": "Shooter",
    "simulator": "Simulation",
    "sport": "Sports",
    "strategy": "Strategy",
    "real time strategy (rts)": "Strategy",
    "turn-based strategy (tbs)": "Strategy",
    "tactical": "Strategy",
    "moba": "Strategy",
    "music": "Misc",
    "party": "Misc",
    "quiz/trivia": "Misc",
    "arcade": "Misc",
    "indie": "Misc",
}

GENRE_PRIORITY = [
    "Racing",
    "Sports",
    "Fighting",
    "Shooter",
    "Platform",
    "Puzzle",
    "Strategy",
    "Role-Playing",
    "Simulation",
    "Adventure",
    "Action",
]

GENRE_THEMES = {item["label"]: item["theme"] for item in GAME_GENRES}
GENRE_THEMES[MISC_GENRE["label"]] = MISC_GENRE["theme"]


def normalize_igdb_genre(name: str) -> str | None:
    """Traduce un genero de IGDB al genero del modelo de ventas."""

    return IGDB_GENRE_TO_SALES.get(name.strip().lower())


def primary_genre(sales_genres) -> str | None:
    """Elige el genero principal de un juego segun la prioridad definida."""

    available = {genre for genre in sales_genres if genre in GENRE_PRIORITY}
    for genre in GENRE_PRIORITY:
        if genre in available:
            return genre
    return None
