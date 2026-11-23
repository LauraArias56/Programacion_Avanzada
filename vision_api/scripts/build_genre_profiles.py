"""Genera perfiles tipicos de ventas para cada genero de videojuego.

Lee el CSV usado por la API de regresion y calcula, por genero, la plataforma
y editorial mas frecuentes y el ano mediano. El resultado se expone en
``/model/genres`` y lo consume la webapp para construir el perfil de ventas.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import config
from src.game_classes import GENRE_THEMES, SALES_GENRES

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SALES_CSV = (
    ROOT / "API_regresion_lineal_multiple" / "data" / "video_games_sales.csv"
)
DEFAULT_METADATA = (
    ROOT / "API_regresion_lineal_multiple" / "artifacts" / "metadata.json"
)


def top_values(series: pd.Series, limit: int = 3) -> list[str]:
    counts = series.dropna().astype(str).value_counts()
    return [str(value) for value in counts.head(limit).index.tolist()]


def build_profiles(sales_csv: Path, metadata_path: Path) -> dict:
    frame = pd.read_csv(sales_csv)
    required = {"platform", "genre", "publisher", "year"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Faltan columnas en el CSV de ventas: " + ", ".join(sorted(missing))
        )

    allowed_platforms: list[str] = []
    year_range = [1980, 2020]
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        allowed_platforms = list(metadata.get("allowed_platforms") or [])
        year_range = list(metadata.get("year_range") or year_range)

    fallback_platform = (
        allowed_platforms[0] if allowed_platforms else str(frame["platform"].mode()[0])
    )
    fallback_year = int(frame["year"].median())

    profiles: dict[str, dict] = {}
    for genre in SALES_GENRES:
        subset = frame[frame["genre"] == genre]
        if subset.empty:
            profiles[genre] = {
                "theme": GENRE_THEMES.get(genre, "genero mixto"),
                "platform": fallback_platform,
                "publisher": "Other",
                "year": fallback_year,
                "sample_size": 0,
                "top_platforms": [],
                "top_publishers": [],
                "year_p25": fallback_year,
                "year_p75": fallback_year,
            }
            continue

        years = subset["year"].dropna()
        year = int(years.median()) if not years.empty else fallback_year
        year = min(max(year, int(year_range[0])), int(year_range[1]))
        platform = str(subset["platform"].mode().iloc[0])
        publisher = str(subset["publisher"].mode().iloc[0])
        profiles[genre] = {
            "theme": GENRE_THEMES.get(genre, "genero mixto"),
            "platform": platform,
            "publisher": publisher,
            "year": year,
            "sample_size": int(len(subset)),
            "top_platforms": top_values(subset["platform"]),
            "top_publishers": top_values(subset["publisher"]),
            "year_p25": int(years.quantile(0.25)) if not years.empty else year,
            "year_p75": int(years.quantile(0.75)) if not years.empty else year,
        }

    return {
        "source": str(sales_csv),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_games": int(len(frame)),
        "year_range": year_range,
        "genres": profiles,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula perfiles de plataforma/editorial/ano por genero."
    )
    parser.add_argument("--sales-csv", type=Path, default=DEFAULT_SALES_CSV)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=config.GAME_PROFILES_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.sales_csv.exists():
        raise SystemExit(f"No existe el CSV de ventas: {args.sales_csv}")

    payload = build_profiles(args.sales_csv, args.metadata)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Perfiles guardados en: {args.output}")
    for genre, profile in payload["genres"].items():
        print(
            f"  {genre}: {profile['platform']} | {profile['publisher']} | "
            f"{profile['year']} ({profile['sample_size']} juegos)"
        )


if __name__ == "__main__":
    main()
