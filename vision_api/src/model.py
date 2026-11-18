"""Arquitectura MobileNetV3-Small adaptada a CIFAR-10."""

import torch
import torch.nn as nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

NUM_CLASSES = 10


def build_model(num_classes: int = NUM_CLASSES, pretrained: bool = False) -> nn.Module:
    """Crea el modelo con una cabeza nueva para CIFAR-10.

    La cabeza del modelo original tiene 1000 salidas. Se reemplaza por un
    clasificador pequeno que trabaja sobre las 576 caracteristicas del backbone.
    El backbone se inicializa con pesos de ImageNet cuando ``pretrained=True``.
    """

    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    model = mobilenet_v3_small(weights=weights)
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 512),
        nn.Hardswish(),
        nn.Dropout(p=0.2),
        nn.Linear(512, num_classes),
    )
    return model


def build_feature_extractor(model: nn.Module) -> nn.Module:
    """Backbone congelado que devuelve un vector de 576 dimensiones."""

    for parameter in model.parameters():
        parameter.requires_grad_(False)

    extractor = nn.Sequential(
        model.features,
        model.avgpool,
        nn.Flatten(),
    )
    extractor.eval()
    return extractor


def load_checkpoint(path, map_location="cpu"):
    """Carga el checkpoint completo y reconstruye el modelo."""

    checkpoint = torch.load(path, map_location=map_location, weights_only=False)
    classes = checkpoint["classes"]
    model = build_model(num_classes=len(classes), pretrained=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model, checkpoint
