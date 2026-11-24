"""Descarga portadas de IGDB y construye el manifest de generos.

El script necesita credenciales de Twitch/IGDB en el entorno:

    IGDB_CLIENT_ID=...
    IGDB_CLIENT_SECRET=...

Las imagenes se guardan en ``vision_api/data/game_covers`` (ignorado por Git).
Solo se versionan el manifest y los artefactos del modelo.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

from src import config
from src.game_classes import (
    GAME_LABELS,
    GAME_LABELS_ES,
    GENRE_PRIORITY,
    normalize_igdb_genre,
    primary_genre,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

IGDB_API = "https://api.igdb.com/v4"
IGDB_COVER_URL = (
    "https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
)
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
MANIFEST_FIELDS = [
    "game_id",
    "title",
    "genre",
    "genre_es",
    "source_genres",
    "platforms",
    "release_year",
    "image_path",
    "image_url",
    "source",
    "split",
]
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


@dataclass
class Candidate:
    game_id: str
    title: str
    genre: str
    source_genres: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    release_year: int | None = None
    image_id: str | None = None
    image_url: str | None = None
    image_path: Path | None = None
    source: str = "IGDB"
    split: str = ""
    rating_count: int = 0


class IGDBClient:
    """Cliente minimo de IGDB con refresh de token y rate limit."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._last_request = 0.0

    def _refresh_token(self) -> None:
        response = self.session.post(
            TWITCH_TOKEN_URL,
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.monotonic() + int(payload.get("expires_in", 3600))

    def _headers(self) -> dict:
        if self._token is None or time.monotonic() >= self._token_expires_at:
            self._refresh_token()
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    def post(self, endpoint: str, body: str) -> list[dict]:
        url = f"{IGDB_API}/{endpoint}"
        for attempt in range(1, 4):
            wait = 0.26 - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            response = self.session.post(
                url, headers=self._headers(), data=body, timeout=30
            )
            self._last_request = time.monotonic()
            if response.status_code == 401 and attempt == 1:
                self._token = None
                continue
            if response.status_code == 429:
                time.sleep(1.5 * attempt)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError(f"IGDB no respondio correctamente a {endpoint}")

    def genres(self) -> list[dict]:
        return self.post("genres", "fields id,name,slug; limit 50;")


def normalize_title(title: str) -> str:
    """Normaliza titulos para reducir duplicados por ediciones."""

    value = title.lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    words = [word for word in value.split() if word not in EDITION_WORDS]
    return " ".join(words).strip()


def release_year(value) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).year
    except (TypeError, ValueError, OSError):
        return None


def build_candidates(client: IGDBClient, args: argparse.Namespace) -> list[Candidate]:
    genre_rows = client.genres()
    igdb_genres_by_sales: dict[str, list[int]] = {label: [] for label in GAME_LABELS}
    for row in genre_rows:
        sales_genre = normalize_igdb_genre(row.get("name", ""))
        if sales_genre in igdb_genres_by_sales:
            igdb_genres_by_sales[sales_genre].append(int(row["id"]))

    missing = [label for label, ids in igdb_genres_by_sales.items() if not ids]
    if missing:
        raise RuntimeError(
            "No se encontraron generos de IGDB para: " + ", ".join(missing)
        )

    selected: dict[str, Candidate] = {}
    seen_titles: set[str] = set()

    for target in GENRE_PRIORITY:
        ids = igdb_genres_by_sales[target]
        print(f"Buscando {target} ({len(ids)} generos IGDB)...", flush=True)
        offset = 0
        found = 0
        for _ in range(args.max_pages):
            body = (
                "fields name,genres.name,platforms.name,first_release_date,"
                "cover.image_id,cover.url,rating_count; "
                f"where genres = ({','.join(str(item) for item in ids)}) "
                "& cover != null & category = 0 & version_parent = null "
                "& rating_count >= 5; "
                "sort rating_count desc; "
                f"limit 500; offset {offset};"
            )
            rows = client.post("games", body)
            if not rows:
                break

            for row in rows:
                source_genres = [
                    item.get("name", "")
                    for item in row.get("genres") or []
                    if item.get("name")
                ]
                sales_genres = [
                    genre
                    for genre in (normalize_igdb_genre(name) for name in source_genres)
                    if genre
                ]
                if primary_genre(sales_genres) != target:
                    continue

                game_id = str(row["id"])
                title = str(row.get("name") or f"Juego {game_id}")
                title_key = normalize_title(title)
                if game_id in selected or title_key in seen_titles:
                    continue

                cover = row.get("cover") or {}
                image_id = cover.get("image_id")
                if not image_id:
                    continue

                platforms = [
                    item.get("name", "")
                    for item in row.get("platforms") or []
                    if item.get("name")
                ]
                candidate = Candidate(
                    game_id=game_id,
                    title=title,
                    genre=target,
                    source_genres=source_genres,
                    platforms=platforms,
                    release_year=release_year(row.get("first_release_date")),
                    image_id=image_id,
                    image_url=IGDB_COVER_URL.format(image_id=image_id),
                    rating_count=int(row.get("rating_count") or 0),
                )
                selected[game_id] = candidate
                seen_titles.add(title_key)
                found += 1
                if found >= args.max_per_class:
                    break

            if found >= args.max_per_class:
                break
            offset += len(rows)
            if len(rows) < 500:
                break

        print(f"  {target}: {found} candidatos", flush=True)

    return list(selected.values())


def load_extra_manifest(path: Path) -> list[Candidate]:
    """Carga un manifest adicional, por ejemplo capturas ya descargadas."""

    candidates: list[Candidate] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            genre = (row.get("genre") or "").strip()
            image_path = Path(row.get("image_path") or "")
            if not image_path.is_absolute():
                image_path = (path.parent / image_path).resolve()
            if genre not in GAME_LABELS:
                continue
            if not image_path.exists():
                print(f"  aviso: no existe {image_path}", flush=True)
                continue
            split = (row.get("split") or "").strip().lower()
            candidates.append(
                Candidate(
                    game_id=str(row.get("game_id") or image_path.stem),
                    title=str(row.get("title") or image_path.stem),
                    genre=genre,
                    source_genres=[
                        item.strip()
                        for item in (row.get("source_genres") or "").split("|")
                        if item.strip()
                    ],
                    platforms=[
                        item.strip()
                        for item in (row.get("platforms") or "").split("|")
                        if item.strip()
                    ],
                    release_year=int(row["release_year"])
                    if str(row.get("release_year") or "").isdigit()
                    else None,
                    image_path=image_path,
                    image_url=row.get("image_url") or None,
                    source=row.get("source") or "extra",
                    split=split if split in {"train", "val", "test"} else "",
                )
            )
    return candidates


def download_cover(candidate: Candidate, images_dir: Path) -> Candidate | None:
    destination = images_dir / candidate.genre / f"{candidate.game_id}.jpg"
    if destination.exists():
        candidate.image_path = destination
        return candidate

    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 4):
        try:
            response = requests.get(
                candidate.image_url or "",
                timeout=30,
                headers={"User-Agent": "PRO_avan-academic-dataset/1.0"},
            )
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image.load()
            image.convert("RGB").save(destination, "JPEG", quality=92)
            candidate.image_path = destination
            return candidate
        except (requests.RequestException, UnidentifiedImageError, OSError):
            if attempt == 3:
                return None
            time.sleep(0.5 * attempt)
    return None


def split_candidates(
    candidates: list[Candidate], seed: int
) -> list[Candidate]:
    """Asigna split por clase respetando grupos de juego."""

    rng = random.Random(seed)
    by_genre: dict[str, list[Candidate]] = {label: [] for label in GAME_LABELS}
    for candidate in candidates:
        by_genre.setdefault(candidate.genre, []).append(candidate)

    for genre, items in by_genre.items():
        pending = [item for item in items if not item.split]
        rng.shuffle(pending)
        if pending:
            total = len(pending)
            train_end = max(1, int(total * 0.70))
            val_end = max(train_end + 1, int(total * 0.85))
            val_end = min(val_end, total - 1) if total >= 3 else total
            for index, candidate in enumerate(pending):
                if index < train_end:
                    candidate.split = "train"
                elif index < val_end:
                    candidate.split = "val"
                else:
                    candidate.split = "test"

    return candidates


def write_manifest(candidates: list[Candidate], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for candidate in sorted(candidates, key=lambda item: (item.genre, item.title)):
            writer.writerow(
                {
                    "game_id": candidate.game_id,
                    "title": candidate.title,
                    "genre": candidate.genre,
                    "genre_es": GAME_LABELS_ES[GAME_LABELS.index(candidate.genre)],
                    "source_genres": "|".join(candidate.source_genres),
                    "platforms": "|".join(candidate.platforms),
                    "release_year": candidate.release_year or "",
                    "image_path": str(candidate.image_path or ""),
                    "image_url": candidate.image_url or "",
                    "source": candidate.source,
                    "split": candidate.split,
                }
            )


def summarize(candidates: list[Candidate]) -> dict:
    summary: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        counts = summary.setdefault(candidate.genre, {"train": 0, "val": 0, "test": 0})
        counts[candidate.split] = counts.get(candidate.split, 0) + 1
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descarga portadas de IGDB y genera el manifest de generos."
    )
    parser.add_argument("--data-dir", type=Path, default=config.GAME_DATA_DIR)
    parser.add_argument("--min-per-class", type=int, default=300)
    parser.add_argument("--max-per-class", type=int, default=1200)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--extra-manifest",
        type=Path,
        default=None,
        help="CSV adicional con capturas o imagenes ya descargadas.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Continua aunque alguna clase no alcance el minimo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_id = os.getenv("IGDB_CLIENT_ID", "").strip()
    client_secret = os.getenv("IGDB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "Faltan IGDB_CLIENT_ID e IGDB_CLIENT_SECRET. "
            "Crealos en el portal de desarrolladores de Twitch."
        )

    args.data_dir.mkdir(parents=True, exist_ok=True)
    images_dir = args.data_dir / "images"

    client = IGDBClient(client_id, client_secret)
    candidates = build_candidates(client, args)
    if args.extra_manifest:
        extra = load_extra_manifest(args.extra_manifest)
        print(f"Manifest adicional: {len(extra)} imagenes", flush=True)
        candidates.extend(extra)

    counts = {label: 0 for label in GAME_LABELS}
    for candidate in candidates:
        counts[candidate.genre] = counts.get(candidate.genre, 0) + 1
    print("Candidatos por genero:", counts, flush=True)

    low = [label for label, count in counts.items() if count < args.min_per_class]
    if low and not args.allow_partial:
        raise SystemExit(
            "Clases por debajo del minimo: "
            + ", ".join(f"{label} ({counts[label]})" for label in low)
            + ". Usa --allow-partial o aumenta --max-pages."
        )

    to_download = [item for item in candidates if item.image_path is None]
    downloaded: list[Candidate] = [
        item for item in candidates if item.image_path is not None
    ]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(download_cover, candidate, images_dir): candidate
            for candidate in to_download
        }
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Portadas"
        ):
            result = future.result()
            if result is not None:
                downloaded.append(result)

    hashes: dict[str, Candidate] = {}
    unique: list[Candidate] = []
    for candidate in downloaded:
        if candidate.image_path is None:
            continue
        digest = hashlib.sha256(candidate.image_path.read_bytes()).hexdigest()
        if digest in hashes:
            continue
        hashes[digest] = candidate
        unique.append(candidate)

    unique = split_candidates(unique, args.seed)
    manifest_path = args.data_dir / "manifest.csv"
    write_manifest(unique, manifest_path)
    summary = summarize(unique)

    print(f"\nManifest: {manifest_path}", flush=True)
    for genre, split_counts in summary.items():
        total = sum(split_counts.values())
        print(f"  {genre}: {total} {split_counts}", flush=True)
    print(f"Total: {len(unique)} imagenes", flush=True)


if __name__ == "__main__":
    main()
