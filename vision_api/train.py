"""Entrenamiento por Transfer Learning sobre CIFAR-10.

Estrategia:
  1. Se cargan pesos de ImageNet en MobileNetV3-Small.
  2. Se congelan las capas convolucionales y se extraen caracteristicas una vez.
  3. Se entrena la cabeza clasificadora sobre esas caracteristicas.
  4. Se guardan el modelo, las clases, las metricas, la matriz de confusion
     y las curvas de entrenamiento.

El resultado es un modelo pequeno, rapido en CPU y facil de desplegar.
"""

import argparse
import json
import os
import random
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader, Subset
from torchvision.datasets import CIFAR10

from src import config
from src.classes import CIFAR10_CLASSES, CIFAR10_LABELS_ES
from src.model import build_feature_extractor, build_model
from src.transforms import build_transform

CIFAR10_MIRROR = os.getenv(
    "CIFAR10_URL",
    "https://github.com/Digital-Media/cv_data/releases/download/cifar-10/cifar-10-python.tar.gz",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrena CIFAR-10 con MobileNetV3")
    parser.add_argument("--image-size", type=int, default=160)
    parser.add_argument("--train-subset", type=int, default=20000)
    parser.add_argument("--test-subset", type=int, default=4000)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=config.DATA_DIR,
        help="Directorio donde se descarga CIFAR-10.",
    )
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def stratified_indices(targets, per_class: int, seed: int) -> list[int]:
    """Toma la misma cantidad de imagenes por clase."""

    rng = np.random.default_rng(seed)
    labels = np.asarray(targets)
    indices: list[int] = []
    for class_id in range(len(CIFAR10_CLASSES)):
        class_indices = np.where(labels == class_id)[0]
        rng.shuffle(class_indices)
        indices.extend(class_indices[:per_class].tolist())
    rng.shuffle(indices)
    return indices


def per_class_count(total: int) -> int:
    return max(1, total // len(CIFAR10_CLASSES))


def extract_features(loader, extractor) -> tuple[torch.Tensor, torch.Tensor]:
    features: list[torch.Tensor] = []
    labels: list[torch.Tensor] = []
    total = len(loader)
    with torch.inference_mode():
        for batch_index, (images, targets) in enumerate(loader, start=1):
            features.append(extractor(images))
            labels.append(targets)
            if batch_index % 25 == 0 or batch_index == total:
                print(f"  caracteristicas {batch_index}/{total}", flush=True)
    return torch.cat(features), torch.cat(labels)


def evaluate_head(head, features, labels) -> tuple[float, float]:
    head.eval()
    with torch.inference_mode():
        logits = head(features)
        loss = nn.functional.cross_entropy(logits, labels).item()
        predictions = logits.argmax(dim=1)
        accuracy = (predictions == labels).float().mean().item()
    return loss, accuracy


def train_head(head, train_features, train_labels, test_features, test_labels, args):
    optimizer = torch.optim.AdamW(
        head.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    best_state = deepcopy(head.state_dict())
    best_accuracy = 0.0
    history = {"epoch": [], "train_loss": [], "train_accuracy": [], "test_accuracy": []}

    for epoch in range(1, args.epochs + 1):
        head.train()
        permutation = torch.randperm(train_features.size(0))
        total_loss = 0.0
        total_items = 0

        for start in range(0, len(permutation), args.batch_size):
            indices = permutation[start : start + args.batch_size]
            batch_features = train_features[indices]
            batch_labels = train_labels[indices]

            optimizer.zero_grad()
            logits = head(batch_features)
            loss = criterion(logits, batch_labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(indices)
            total_items += len(indices)

        train_loss = total_loss / max(total_items, 1)
        _, train_accuracy = evaluate_head(head, train_features, train_labels)
        _, test_accuracy = evaluate_head(head, test_features, test_labels)

        history["epoch"].append(epoch)
        history["train_loss"].append(round(train_loss, 6))
        history["train_accuracy"].append(round(train_accuracy, 6))
        history["test_accuracy"].append(round(test_accuracy, 6))

        if test_accuracy > best_accuracy:
            best_accuracy = test_accuracy
            best_state = deepcopy(head.state_dict())

        print(
            f"epoca {epoch:02d}/{args.epochs} "
            f"loss={train_loss:.4f} train_acc={train_accuracy:.4f} "
            f"test_acc={test_accuracy:.4f}",
            flush=True,
        )

    head.load_state_dict(best_state)
    return history, best_accuracy


def jsonable(value):
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    if hasattr(value, "item"):
        return value.item()
    return value


def denormalize(tensor: torch.Tensor) -> np.ndarray:
    mean = torch.tensor(config.IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(config.IMAGENET_STD).view(3, 1, 1)
    image = (tensor.cpu() * std + mean).clamp(0, 1)
    return image.permute(1, 2, 0).numpy()


def save_confusion_matrix(matrix, path: Path, labels: list[str]) -> None:
    figure, axis = plt.subplots(figsize=(9, 8))
    image = axis.imshow(matrix, interpolation="nearest", cmap="Blues")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axis.set(
        xticks=np.arange(len(labels)),
        yticks=np.arange(len(labels)),
        xticklabels=labels,
        yticklabels=labels,
        ylabel="Etiqueta real",
        xlabel="Etiqueta predicha",
        title="Matriz de confusion - CIFAR-10",
    )
    plt.setp(axis.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    threshold = matrix.max() / 2.0
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(
                column,
                row,
                str(matrix[row, column]),
                ha="center",
                va="center",
                color="white" if matrix[row, column] > threshold else "black",
                fontsize=8,
            )
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_curves(history: dict, path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(history["epoch"], history["train_loss"], color="#1f3a5f")
    axes[0].set(title="Perdida de entrenamiento", xlabel="Epoca", ylabel="Loss")
    axes[0].grid(alpha=0.25)

    axes[1].plot(
        history["epoch"], history["train_accuracy"], label="Train", color="#1f3a5f"
    )
    axes[1].plot(
        history["epoch"], history["test_accuracy"], label="Test", color="#d97706"
    )
    axes[1].set(title="Accuracy por epoca", xlabel="Epoca", ylabel="Accuracy")
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_sample_predictions(model, dataset, path: Path, sample_count: int = 16) -> None:
    model.eval()
    columns = 4
    rows = max(1, sample_count // columns)
    figure, axes = plt.subplots(rows, columns, figsize=(12, 3 * rows))
    axes = np.atleast_1d(axes).ravel()

    for index in range(rows * columns):
        image, true_label = dataset[index]
        with torch.inference_mode():
            logits = model(image.unsqueeze(0))
            probabilities = torch.softmax(logits, dim=1)[0]
            predicted_label = int(probabilities.argmax().item())
            confidence = float(probabilities[predicted_label].item())

        axis = axes[index]
        axis.imshow(denormalize(image))
        color = "#15803d" if predicted_label == true_label else "#b91c1c"
        axis.set_title(
            f"real: {CIFAR10_LABELS_ES[true_label]}\n"
            f"pred: {CIFAR10_LABELS_ES[predicted_label]} ({confidence:.1%})",
            fontsize=8,
            color=color,
        )
        axis.axis("off")

    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))

    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    figures_dir = config.ARTIFACTS_DIR / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)

    print("Cargando CIFAR-10 y pesos preentrenados...", flush=True)
    CIFAR10.url = CIFAR10_MIRROR
    transform = build_transform(args.image_size)
    train_dataset = CIFAR10(
        root=str(args.data_dir), train=True, download=True, transform=transform
    )
    test_dataset = CIFAR10(
        root=str(args.data_dir), train=False, download=True, transform=transform
    )

    train_indices = stratified_indices(
        train_dataset.targets, per_class_count(args.train_subset), args.seed
    )
    test_indices = stratified_indices(
        test_dataset.targets, per_class_count(args.test_subset), args.seed + 1
    )
    train_subset = Subset(train_dataset, train_indices)
    test_subset = Subset(test_dataset, test_indices)
    print(
        f"Train: {len(train_subset)} imagenes | Test: {len(test_subset)} imagenes",
        flush=True,
    )

    train_loader = DataLoader(
        train_subset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )
    test_loader = DataLoader(
        test_subset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )

    model = build_model(num_classes=len(CIFAR10_CLASSES), pretrained=True)
    extractor = build_feature_extractor(model)
    for parameter in model.classifier.parameters():
        parameter.requires_grad_(True)

    print("Extrayendo caracteristicas del conjunto de entrenamiento...", flush=True)
    train_features, train_labels = extract_features(train_loader, extractor)
    print("Extrayendo caracteristicas del conjunto de test...", flush=True)
    test_features, test_labels = extract_features(test_loader, extractor)
    print(
        f"Dimension de caracteristicas: {train_features.shape}",
        flush=True,
    )

    print("Entrenando la cabeza clasificadora...", flush=True)
    history, best_accuracy = train_head(
        model.classifier,
        train_features,
        train_labels,
        test_features,
        test_labels,
        args,
    )

    model.eval()
    with torch.inference_mode():
        test_logits = model.classifier(test_features)
        test_predictions = test_logits.argmax(dim=1).cpu().numpy()
    true_labels = test_labels.cpu().numpy()

    matrix = confusion_matrix(true_labels, test_predictions)
    report = classification_report(
        true_labels,
        test_predictions,
        target_names=CIFAR10_LABELS_ES,
        output_dict=True,
        zero_division=0,
    )
    accuracy = float((test_predictions == true_labels).mean())
    stamp = datetime.now(timezone.utc)
    model_version = f"cifar10-mobilenetv3-{stamp.strftime('%Y%m%d.%H%M%S')}"

    metrics = {
        "model_version": model_version,
        "trained_at": stamp.isoformat(),
        "architecture": "mobilenet_v3_small",
        "dataset": {
            "name": "CIFAR-10",
            "source": "torchvision.datasets.CIFAR10",
            "train_samples": len(train_subset),
            "test_samples": len(test_subset),
            "classes": [item["label_es"] for item in CIFAR10_CLASSES],
            "note": (
                "Subconjunto balanceado de CIFAR-10. El dataset completo tiene "
                "50000 imagenes de entrenamiento y 10000 de test."
            ),
        },
        "preprocessing": {
            "image_size": args.image_size,
            "color": "RGB",
            "mean": config.IMAGENET_MEAN,
            "std": config.IMAGENET_STD,
            "tensor_layout": "NCHW",
        },
        "transfer_learning": {
            "backbone": "MobileNetV3-Small",
            "pretrained_weights": "ImageNet IMAGENET1K_V1",
            "strategy": "backbone congelado + fine-tuning de la cabeza clasificadora",
            "feature_dim": int(train_features.shape[1]),
            "epochs": args.epochs,
            "best_test_accuracy_during_training": round(best_accuracy, 6),
        },
        "test_accuracy": round(accuracy, 6),
        "macro_precision": round(report["macro avg"]["precision"], 6),
        "macro_recall": round(report["macro avg"]["recall"], 6),
        "macro_f1": round(report["macro avg"]["f1-score"], 6),
        "weighted_f1": round(report["weighted avg"]["f1-score"], 6),
        "per_class": {
            label: {
                "precision": round(report[label]["precision"], 6),
                "recall": round(report[label]["recall"], 6),
                "f1": round(report[label]["f1-score"], 6),
                "support": int(report[label]["support"]),
            }
            for label in CIFAR10_LABELS_ES
        },
        "confusion_matrix": matrix.tolist(),
        "history": history,
    }

    figures = {
        "confusion_matrix": "confusion_matrix.png",
        "training_curves": "training_curves.png",
        "sample_predictions": "sample_predictions.png",
    }
    save_confusion_matrix(
        matrix, figures_dir / figures["confusion_matrix"], CIFAR10_LABELS_ES
    )
    save_curves(history, figures_dir / figures["training_curves"])
    save_sample_predictions(
        model, test_subset, figures_dir / figures["sample_predictions"]
    )
    metrics["figures"] = {key: f"figures/{value}" for key, value in figures.items()}

    checkpoint = {
        "state_dict": model.state_dict(),
        "classes": CIFAR10_CLASSES,
        "model_version": model_version,
        "architecture": "mobilenet_v3_small",
        "dataset": metrics["dataset"],
        "metrics": metrics,
        "image_size": args.image_size,
        "preprocessing": metrics["preprocessing"],
    }

    torch.save(checkpoint, config.MODEL_PATH)
    config.CLASSES_PATH.write_text(
        json.dumps(CIFAR10_CLASSES, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    config.METRICS_PATH.write_text(
        json.dumps(jsonable(metrics), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nModelo guardado en:", config.MODEL_PATH)
    print("Clases guardadas en:", config.CLASSES_PATH)
    print("Metricas guardadas en:", config.METRICS_PATH)
    print(f"Accuracy test: {accuracy:.4f}")
    print(f"Macro F1 test: {metrics['macro_f1']:.4f}")
    print("Figuras en:", figures_dir)


if __name__ == "__main__":
    main()
