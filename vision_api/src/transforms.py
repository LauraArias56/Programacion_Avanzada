"""Preprocesamiento de imagenes compatible con el modelo preentrenado."""

from torchvision import transforms

from .config import IMAGENET_MEAN, IMAGENET_STD, IMAGE_SIZE


def build_transform(image_size: int = IMAGE_SIZE) -> transforms.Compose:
    """RGB, redimensionado cuadrado, tensor NCHW y normalizacion ImageNet."""

    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )
