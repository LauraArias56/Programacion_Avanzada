"""Valida el manifest de generos antes de entrenar."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from PIL import Image, UnidentifiedImageError

from src import config
from src.game_classes import GAME_LABELS

REQUIRED_COLUMNS = {
    "game_id",
    "title",
    "genre",
    "image_path",
    "split",
}
VALID_SPLITS = {"train", "val", "test"}
EDITION_WORDS = {
    "deluxe",
    "definitive",
    "complete",
    "gold",
    "ultimate",
    "premium",
    "remastered",
    "remake",
    "goty",
    "edition",
    "bundle",
    "collection",
}


def normalize_title(title: str) -> str:
    value = str(title).lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(word for word in value.split() if word not in EDITION_WORDS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Comprueba imagenes, clases, splits y duplicados."
    )
    parser.add_argument(
        "--manifest", type=Path, default=config.GAME_DATA_DIR / "manifest.csv"
    )
    parser.add_argument("--min-per-class", type=int, default=300)
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.manifest.exists():
        raise SystemExit(f"No existe el manifest: {args.manifest}")

    frame = pd.read_csv(args.manifest)
    errors: list[str] = []
    warnings: list[str] = []

    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        errors.append("Faltan columnas: " + ", ".join(sorted(missing)))

    if frame.empty:
        errors.append("El manifest esta vacio.")

    if not missing:
        invalid_genres = sorted(set(frame["genre"]) - set(GAME_LABELS))
        if invalid_genres:
            errors.append("Generos no permitidos: " + ", ".join(invalid_genres))

        invalid_splits = sorted(set(frame["split"]) - VALID_SPLITS)
        if invalid_splits:
            errors.append("Splits no validos: " + ", ".join(invalid_splits))

        counts = frame["genre"].value_counts().to_dict()
        for genre in GAME_LABELS:
            count = int(counts.get(genre, 0))
            if count < args.min_per_class:
                errors.append(
                    f"{genre} tiene {count} imagenes; minimo {args.min_per_class}."
                )

        for genre in GAME_LABELS:
            subset = frame[frame["genre"] == genre]
            for split in ("val", "test"):
                if subset.empty or not (subset["split"] == split).any():
                    warnings.append(f"{genre} no tiene imagenes en {split}.")

        leakage = frame.groupby("game_id")["split"].nunique()
        leaked_ids = leakage[leakage > 1].index.tolist()
        if leaked_ids:
            errors.append(
                "Juegos en mas de un split: " + ", ".join(map(str, leaked_ids[:10]))
            )

        frame["title_key"] = frame["title"].map(normalize_title)
        title_leakage = frame.groupby("title_key")["split"].nunique()
        leaked_titles = title_leakage[title_leakage > 1].index.tolist()
        if leaked_titles:
            warnings.append(
                "Titulos normalizados en mas de un split: "
                + ", ".join(map(str, leaked_titles[:10]))
            )

        missing_images = [
            path for path in frame["image_path"].astype(str) if not Path(path).exists()
        ]
        if missing_images:
            errors.append(f"Faltan {len(missing_images)} imagenes en disco.")

        hashes: dict[str, tuple[str, str]] = {}
        duplicate_count = 0
        corrupt_count = 0
        for row in frame.itertuples(index=False):
            path = Path(str(row.image_path))
            if not path.exists():
                continue
            try:
                with Image.open(path) as image:
                    image.load()
            except (UnidentifiedImageError, OSError):
                corrupt_count += 1
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in hashes:
                duplicate_count += 1
                other_split, other_path = hashes[digest]
                if other_split != row.split:
                    errors.append(
                        f"Imagen duplicada entre splits: {path} y {other_path}."
                    )
            else:
                hashes[digest] = (row.split, str(path))

        if corrupt_count:
            errors.append(f"Imagenes corruptas: {corrupt_count}.")
        if duplicate_count:
            warnings.append(f"Imagenes duplicadas: {duplicate_count}.")

        summary = {
            "total": int(len(frame)),
            "classes": {
                genre: int((frame["genre"] == genre).sum()) for genre in GAME_LABELS
            },
            "splits": frame["split"].value_counts().to_dict(),
            "duplicates": duplicate_count,
            "corrupt": corrupt_count,
        }
    else:
        summary = {}

    report = {
        "manifest": str(args.manifest),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
