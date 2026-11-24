"""Preprocesamiento de imagenes compatible con el modelo preentrenado."""

from torchvision import transforms

from .config import (
    GAME_EVAL_RESIZE,
    GAME_IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    IMAGE_SIZE,
)


def build_transform(image_size: int = IMAGE_SIZE) -> transforms.Compose:
    """RGB, redimensionado cuadrado, tensor NCHW y normalizacion ImageNet."""

    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def build_train_transform(
    image_size: int = GAME_IMAGE_SIZE,
) -> transforms.Compose:
    """Aumentos suaves para portadas y capturas de videojuegos."""

    return transforms.Compose(
        [
            transforms.RandomResizedCrop(image_size, scale=(0.65, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def build_eval_transform(
    image_size: int = GAME_IMAGE_SIZE,
    resize_size: int = GAME_EVAL_RESIZE,
) -> transforms.Compose:
    """Recorte central para evaluacion e inferencia del modelo de generos."""

    return transforms.Compose(
        [
            transforms.Resize(resize_size),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )
