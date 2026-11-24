"""Carga y logica de inferencia del clasificador de generos."""

from pathlib import Path

import torch
from PIL import Image

from src import config
from src.model import load_checkpoint
from src.transforms import build_eval_transform


class GameGenreModelService:
    """Carga el checkpoint de generos una sola vez y atiende peticiones."""

    def __init__(self, model_path: Path | str = config.GAME_MODEL_PATH):
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el modelo de generos {path}. "
                "Ejecuta primero: python train_game_genres.py"
            )

        self._model_path = path
        self.model, checkpoint = load_checkpoint(path)
        self.classes: list[dict] = checkpoint["classes"]
        self.model_version: str = checkpoint["model_version"]
        self.architecture: str = checkpoint.get("architecture", "mobilenet_v3_small")
        self.dataset: dict = checkpoint.get("dataset", {})
        self.metrics: dict = checkpoint.get("metrics", {})
        self.image_size: int = int(
            checkpoint.get("image_size", config.GAME_IMAGE_SIZE)
        )
        self.temperature: float = float(checkpoint.get("temperature", 1.0))
        self.genre_profiles: dict = checkpoint.get("genre_profiles", {})
        self.preprocessing: dict = checkpoint.get(
            "preprocessing",
            {
                "image_size": self.image_size,
                "eval_resize": config.GAME_EVAL_RESIZE,
                "color": "RGB",
                "mean": config.IMAGENET_MEAN,
                "std": config.IMAGENET_STD,
                "tensor_layout": "NCHW",
            },
        )
        self._transform = build_eval_transform(self.image_size)

    def info(self) -> dict:
        return {
            "model_version": self.model_version,
            "architecture": self.architecture,
            "dataset": self.dataset,
            "image_size": self.image_size,
            "num_classes": len(self.classes),
            "classes": self.classes,
            "metrics": self.metrics,
            "preprocessing": self.preprocessing,
            "genre_profiles": self.genre_profiles,
            "disclaimer": (
                "Clasificacion aproximada de genero a partir de portadas o "
                "capturas. Los generos pueden solaparse; usa el top-3 y corrige "
                "el perfil antes de estimar ventas."
            ),
        }

    def predict(self, image: Image.Image, top_k: int = 3) -> dict:
        if image.mode != "RGB":
            image = image.convert("RGB")

        tensor = self._transform(image).unsqueeze(0)
        with torch.inference_mode():
            logits = self.model(tensor)
            probabilities = torch.softmax(logits / self.temperature, dim=1)[0]

        k = max(1, min(top_k, len(self.classes)))
        values, indices = torch.topk(probabilities, k=k)
        top_predictions = []
        for value, index in zip(values.tolist(), indices.tolist()):
            class_info = self.classes[index]
            top_predictions.append(
                {
                    "class_id": int(class_info["id"]),
                    "label": class_info["label"],
                    "label_es": class_info["label_es"],
                    "confidence": round(float(value), 6),
                }
            )

        best = top_predictions[0]
        return {
            "label": best["label"],
            "label_es": best["label_es"],
            "confidence": best["confidence"],
            "top_k": top_predictions,
        }
