"""Carga del modelo y logica de inferencia."""

from pathlib import Path

import torch
from PIL import Image

from src import config
from src.model import load_checkpoint
from src.transforms import build_transform


class VisionModelService:
    """Carga el checkpoint una sola vez y atiende peticiones."""

    def __init__(self, model_path: Path | str = config.MODEL_PATH):
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el modelo {path}. Ejecuta primero: python train.py"
            )

        self._model_path = path
        self.model, checkpoint = load_checkpoint(path)
        self.classes: list[dict] = checkpoint["classes"]
        self.model_version: str = checkpoint["model_version"]
        self.architecture: str = checkpoint.get("architecture", "mobilenet_v3_small")
        self.dataset: dict = checkpoint.get("dataset", {})
        self.metrics: dict = checkpoint.get("metrics", {})
        self.image_size: int = int(checkpoint.get("image_size", config.IMAGE_SIZE))
        self.preprocessing: dict = checkpoint.get(
            "preprocessing",
            {
                "resize": [self.image_size, self.image_size],
                "color": "RGB",
                "mean": config.IMAGENET_MEAN,
                "std": config.IMAGENET_STD,
                "tensor_layout": "NCHW",
            },
        )
        self._transform = build_transform(self.image_size)

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
            "disclaimer": (
                "Clasificacion aproximada sobre CIFAR-10. Las imagenes de camara "
                "pueden no coincidir con la distribucion del dataset; usa el "
                "resultado como demostracion del flujo de vision."
            ),
        }

    def predict(self, image: Image.Image, top_k: int = 3) -> dict:
        if image.mode != "RGB":
            image = image.convert("RGB")

        tensor = self._transform(image).unsqueeze(0)
        with torch.inference_mode():
            logits = self.model(tensor)
            probabilities = torch.softmax(logits, dim=1)[0]

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
