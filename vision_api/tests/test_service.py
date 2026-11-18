"""Prueba de humo del modelo real cuando existen los artefactos."""

from pathlib import Path

import pytest
from PIL import Image

from api.service import VisionModelService
from src import config


@pytest.mark.skipif(
    not Path(config.MODEL_PATH).exists(), reason="model.pt no entrenado"
)
def test_real_model_predicts_top_k():
    service = VisionModelService()
    image = Image.new("RGB", (64, 64), "blue")

    result = service.predict(image, top_k=3)

    assert result["label"]
    assert 0 <= result["confidence"] <= 1
    assert len(result["top_k"]) == 3
    assert result["top_k"][0]["confidence"] >= result["top_k"][-1]["confidence"]
