"""Entrena el clasificador de generos de videojuego.

Estrategia CPU-friendly:
  1. MobileNetV3-Small preentrenado en ImageNet con backbone congelado.
  2. Se extraen caracteristicas de varias vistas aumentadas por imagen.
  3. Se entrena la cabeza clasificadora con pesos por clase y label smoothing.
  4. Opcionalmente se desbloquea el ultimo bloque para fine-tuning.
  5. Se guardan checkpoint, metricas, calibracion y figuras.
"""

from __future__ import annotations

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
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Dataset

from src import config
from src.game_classes import GAME_GENRES, GAME_LABELS, GAME_LABELS_ES
from src.model import build_feature_extractor, build_model
from src.transforms import build_eval_transform, build_train_transform


class ManifestDataset(Dataset):
    """Dataset de imagenes descrito por el manifest de generos."""

    def __init__(self, frame: pd.DataFrame, transform):
        self.paths = frame["image_path"].astype(str).tolist()
        self.labels = [GAME_LABELS.index(genre) for genre in frame["genre"]]
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int):
        with Image.open(self.paths[index]) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, self.labels[index]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrena el clasificador de generos de videojuego."
    )
    parser.add_argument(
        "--manifest", type=Path, default=config.GAME_DATA_DIR / "manifest.csv"
    )
    parser.add_argument("--output-dir", type=Path, default=config.GAME_ARTIFACTS_DIR)
    parser.add_argument("--profiles", type=Path, default=config.GAME_PROFILES_PATH)
    parser.add_argument("--image-size", type=int, default=config.GAME_IMAGE_SIZE)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.1)
    parser.add_argument("--augment-views", type=int, default=3)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--unfreeze-last-block", action="store_true")
    parser.add_argument("--finetune-epochs", type=int, default=3)
    parser.add_argument("--finetune-lr", type=float, default=1e-4)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def extract_features(loader, extractor) -> tuple[torch.Tensor, torch.Tensor]:
    features: list[torch.Tensor] = []
    labels: list[torch.Tensor] = []
    total = len(loader)
    with torch.inference_mode():
        for index, (images, targets) in enumerate(loader, start=1):
            features.append(extractor(images))
            labels.append(targets)
            if index % 25 == 0 or index == total:
                print(f"  caracteristicas {index}/{total}", flush=True)
    return torch.cat(features), torch.cat(labels)


def topk_accuracy(logits: torch.Tensor, labels: torch.Tensor, k: int) -> float:
    k = min(k, logits.size(1))
    _, indices = logits.topk(k, dim=1)
    correct = indices.eq(labels.view(-1, 1)).any(dim=1)
    return float(correct.float().mean().item())


def evaluate_logits(
    logits: torch.Tensor, labels: torch.Tensor
) -> tuple[float, float, float, float]:
    logits = logits.float()
    loss = nn.functional.cross_entropy(logits, labels).item()
    predictions = logits.argmax(dim=1)
    accuracy = float((predictions == labels).float().mean().item())
    top3 = topk_accuracy(logits, labels, 3)
    macro_f1 = float(
        f1_score(
            labels.cpu().numpy(),
            predictions.cpu().numpy(),
            average="macro",
            zero_division=0,
        )
    )
    return loss, accuracy, top3, macro_f1


def class_weights(labels: torch.Tensor, num_classes: int) -> torch.Tensor:
    counts = torch.bincount(labels, minlength=num_classes).float()
    weights = 1.0 / counts.clamp(min=1)
    return weights / weights.sum() * num_classes


def train_head(
    head,
    train_features,
    train_labels,
    val_features,
    val_labels,
    args,
    weights,
) -> tuple[dict, dict, float]:
    optimizer = torch.optim.AdamW(
        head.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(args.epochs, 1)
    )
    criterion = nn.CrossEntropyLoss(
        weight=weights, label_smoothing=args.label_smoothing
    )
    best_state = deepcopy(head.state_dict())
    best_f1 = 0.0
    best_epoch = 0
    patience = 0
    history = {
        "epoch": [],
        "train_loss": [],
        "train_accuracy": [],
        "val_accuracy": [],
        "val_top3_accuracy": [],
        "val_macro_f1": [],
    }

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

        scheduler.step()
        train_loss = total_loss / max(total_items, 1)
        head.eval()
        with torch.inference_mode():
            _, train_accuracy, _, _ = evaluate_logits(
                head(train_features), train_labels
            )
            val_loss, val_accuracy, val_top3, val_f1 = evaluate_logits(
                head(val_features), val_labels
            )

        history["epoch"].append(epoch)
        history["train_loss"].append(round(train_loss, 6))
        history["train_accuracy"].append(round(train_accuracy, 6))
        history["val_accuracy"].append(round(val_accuracy, 6))
        history["val_top3_accuracy"].append(round(val_top3, 6))
        history["val_macro_f1"].append(round(val_f1, 6))

        print(
            f"epoca {epoch:02d}/{args.epochs} loss={train_loss:.4f} "
            f"train_acc={train_accuracy:.4f} val_acc={val_accuracy:.4f} "
            f"val_top3={val_top3:.4f} val_f1={val_f1:.4f} "
            f"val_loss={val_loss:.4f}",
            flush=True,
        )

        if val_f1 > best_f1:
            best_f1 = val_f1
            best_epoch = epoch
            best_state = deepcopy(head.state_dict())
            patience = 0
        else:
            patience += 1
            if patience >= args.patience:
                print("Early stopping.", flush=True)
                break

    head.load_state_dict(best_state)
    return history, best_state, best_epoch


def fine_tune(
    model,
    train_dataset,
    val_dataset,
    args,
    weights,
) -> dict:
    """Fine-tuning opcional del ultimo bloque convolucional."""

    for parameter in model.features[-1].parameters():
        parameter.requires_grad_(True)

    optimizer = torch.optim.AdamW(
        [
            {"params": model.features[-1].parameters(), "lr": args.finetune_lr},
            {"params": model.classifier.parameters(), "lr": args.lr},
        ],
        weight_decay=args.weight_decay,
    )
    criterion = nn.CrossEntropyLoss(
        weight=weights, label_smoothing=args.label_smoothing
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )
    best_state = deepcopy(model.state_dict())
    best_f1 = 0.0
    best_epoch = 0
    history = {"epoch": [], "val_accuracy": [], "val_top3_accuracy": [], "val_macro_f1": []}

    for epoch in range(1, args.finetune_epochs + 1):
        model.train()
        total_loss = 0.0
        total_items = 0
        for images, targets in train_loader:
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(targets)
            total_items += len(targets)

        model.eval()
        val_logits: list[torch.Tensor] = []
        val_labels: list[torch.Tensor] = []
        with torch.inference_mode():
            for images, targets in val_loader:
                val_logits.append(model(images))
                val_labels.append(targets)
        logits = torch.cat(val_logits)
        labels = torch.cat(val_labels)
        val_loss, accuracy, top3, macro_f1 = evaluate_logits(logits, labels)

        history["epoch"].append(epoch)
        history["val_accuracy"].append(round(accuracy, 6))
        history["val_top3_accuracy"].append(round(top3, 6))
        history["val_macro_f1"].append(round(macro_f1, 6))

        print(
            f"finetune {epoch:02d}/{args.finetune_epochs} "
            f"loss={total_loss / max(total_items, 1):.4f} "
            f"val_acc={accuracy:.4f} val_top3={top3:.4f} "
            f"val_f1={macro_f1:.4f} val_loss={val_loss:.4f}",
            flush=True,
        )

        if macro_f1 > best_f1:
            best_f1 = macro_f1
            best_epoch = epoch
            best_state = deepcopy(model.state_dict())

    model.load_state_dict(best_state)
    return {"history": history, "best_epoch": best_epoch, "best_val_f1": best_f1}


def predict_logits(model, dataset, batch_size: int, workers: int):
    loader = DataLoader(
        dataset, batch_size=batch_size, shuffle=False, num_workers=workers
    )
    model.eval()
    logits: list[torch.Tensor] = []
    labels: list[torch.Tensor] = []
    with torch.inference_mode():
        for images, targets in loader:
            logits.append(model(images))
            labels.append(targets)
    return torch.cat(logits), torch.cat(labels)


def calibrate_temperature(
    logits: torch.Tensor, labels: torch.Tensor
) -> tuple[float, float]:
    best_temperature = 1.0
    best_loss = float("inf")
    for temperature in np.linspace(0.5, 3.0, 26):
        loss = nn.functional.cross_entropy(
            logits / float(temperature), labels
        ).item()
        if loss < best_loss:
            best_loss = loss
            best_temperature = float(temperature)
    return best_temperature, expected_calibration_error(
        logits, labels, best_temperature
    )


def expected_calibration_error(
    logits: torch.Tensor, labels: torch.Tensor, temperature: float = 1.0
) -> float:
    probabilities = torch.softmax(logits / temperature, dim=1)
    confidences, predictions = probabilities.max(dim=1)
    accuracies = predictions.eq(labels).float()
    ece = 0.0
    for lower in np.linspace(0.0, 1.0, 11)[:-1]:
        upper = lower + 0.1
        mask = (confidences >= lower) & (confidences < upper)
        if mask.any():
            ece += (
                torch.abs(accuracies[mask].mean() - confidences[mask].mean())
                * mask.float().mean()
            ).item()
    return float(ece)


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


def save_confusion_matrix(matrix, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(10, 8))
    image = axis.imshow(matrix, interpolation="nearest", cmap="Blues")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axis.set(
        xticks=np.arange(len(GAME_LABELS_ES)),
        yticks=np.arange(len(GAME_LABELS_ES)),
        xticklabels=GAME_LABELS_ES,
        yticklabels=GAME_LABELS_ES,
        ylabel="Genero real",
        xlabel="Genero predicho",
        title="Matriz de confusion - generos de videojuego",
    )
    plt.setp(axis.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    threshold = matrix.max() / 2.0 if matrix.size else 0
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
        history["epoch"], history["val_accuracy"], label="Validacion", color="#d97706"
    )
    axes[1].plot(
        history["epoch"],
        history["val_top3_accuracy"],
        label="Top-3 validacion",
        color="#15803d",
    )
    axes[1].set(title="Accuracy por epoca", xlabel="Epoca", ylabel="Accuracy")
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_sample_predictions(
    model,
    dataset: ManifestDataset,
    temperature: float,
    path: Path,
    sample_count: int = 16,
) -> None:
    model.eval()
    columns = 4
    rows = max(1, sample_count // columns)
    figure, axes = plt.subplots(rows, columns, figsize=(12, 3 * rows))
    axes = np.atleast_1d(axes).ravel()

    for index in range(min(rows * columns, len(dataset))):
        image, true_label = dataset[index]
        with torch.inference_mode():
            logits = model(image.unsqueeze(0))
            probabilities = torch.softmax(logits / temperature, dim=1)[0]
            predicted_label = int(probabilities.argmax().item())
            confidence = float(probabilities[predicted_label].item())

        axis = axes[index]
        axis.imshow(denormalize(image))
        color = "#15803d" if predicted_label == true_label else "#b91c1c"
        axis.set_title(
            f"real: {GAME_LABELS_ES[true_label]}\n"
            f"pred: {GAME_LABELS_ES[predicted_label]} ({confidence:.1%})",
            fontsize=8,
            color=color,
        )
        axis.axis("off")

    for index in range(len(dataset), len(axes)):
        axes[index].axis("off")

    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))

    if not args.manifest.exists():
        raise SystemExit(f"No existe el manifest: {args.manifest}")

    frame = pd.read_csv(args.manifest)
    required = {"image_path", "genre", "split"}
    missing = required - set(frame.columns)
    if missing:
        raise SystemExit(
            "Faltan columnas en el manifest: " + ", ".join(sorted(missing))
        )

    frame = frame[frame["image_path"].astype(str).map(lambda p: Path(p).exists())]
    invalid = sorted(set(frame["genre"]) - set(GAME_LABELS))
    if invalid:
        raise SystemExit("Generos no permitidos: " + ", ".join(invalid))

    train_frame = frame[frame["split"] == "train"].reset_index(drop=True)
    val_frame = frame[frame["split"] == "val"].reset_index(drop=True)
    test_frame = frame[frame["split"] == "test"].reset_index(drop=True)
    if train_frame.empty or val_frame.empty or test_frame.empty:
        raise SystemExit("Los splits train/val/test deben tener imagenes.")

    print(
        f"Train: {len(train_frame)} | Val: {len(val_frame)} | "
        f"Test: {len(test_frame)}",
        flush=True,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = args.output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    model = build_model(num_classes=len(GAME_GENRES), pretrained=True)
    extractor = build_feature_extractor(model)
    for parameter in model.classifier.parameters():
        parameter.requires_grad_(True)

    eval_transform = build_eval_transform(args.image_size)
    val_dataset = ManifestDataset(val_frame, eval_transform)
    test_dataset = ManifestDataset(test_frame, eval_transform)
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )

    print("Extrayendo caracteristicas de validacion y test...", flush=True)
    val_features, val_labels = extract_features(val_loader, extractor)
    test_features, test_labels = extract_features(test_loader, extractor)

    train_features_parts: list[torch.Tensor] = []
    train_labels_parts: list[torch.Tensor] = []
    views = max(1, args.augment_views)
    for view in range(1, views + 1):
        set_seed(args.seed + view)
        train_dataset = ManifestDataset(train_frame, build_train_transform(args.image_size))
        train_loader = DataLoader(
            train_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.workers,
        )
        print(f"Extrayendo caracteristicas train vista {view}/{views}...", flush=True)
        features, labels = extract_features(train_loader, extractor)
        train_features_parts.append(features)
        train_labels_parts.append(labels)

    train_features = torch.cat(train_features_parts)
    train_labels = torch.cat(train_labels_parts)
    print(f"Dimension de caracteristicas: {train_features.shape}", flush=True)

    weights = class_weights(train_labels, len(GAME_GENRES))
    print("Entrenando la cabeza clasificadora...", flush=True)
    history, _, best_epoch = train_head(
        model.classifier,
        train_features,
        train_labels,
        val_features,
        val_labels,
        args,
        weights,
    )

    finetune = None
    if args.unfreeze_last_block:
        print("Fine-tuning del ultimo bloque...", flush=True)
        finetune = fine_tune(
            model,
            ManifestDataset(train_frame, build_train_transform(args.image_size)),
            ManifestDataset(val_frame, eval_transform),
            args,
            weights,
        )

    model.eval()
    test_logits, true_labels = predict_logits(
        model, test_dataset, args.batch_size, args.workers
    )
    val_logits, val_true = predict_logits(
        model, val_dataset, args.batch_size, args.workers
    )

    temperature, val_ece = calibrate_temperature(val_logits, val_true)
    test_ece = expected_calibration_error(test_logits, true_labels, temperature)
    test_probabilities = torch.softmax(test_logits / temperature, dim=1)
    test_predictions = test_probabilities.argmax(dim=1).cpu().numpy()
    true_labels_np = true_labels.cpu().numpy()

    matrix = confusion_matrix(
        true_labels_np, test_predictions, labels=list(range(len(GAME_GENRES)))
    )
    report = classification_report(
        true_labels_np,
        test_predictions,
        labels=list(range(len(GAME_GENRES))),
        target_names=GAME_LABELS_ES,
        output_dict=True,
        zero_division=0,
    )
    accuracy = float((test_predictions == true_labels_np).mean())
    top3_accuracy = topk_accuracy(test_logits, true_labels, 3)

    stamp = datetime.now(timezone.utc)
    model_version = f"gamegenres-mobilenetv3-{stamp.strftime('%Y%m%d.%H%M%S')}"

    class_counts = {
        genre: int((frame["genre"] == genre).sum()) for genre in GAME_LABELS
    }
    split_counts = {
        genre: {
            split: int(
                ((frame["genre"] == genre) & (frame["split"] == split)).sum()
            )
            for split in ("train", "val", "test")
        }
        for genre in GAME_LABELS
    }

    metrics = {
        "model_version": model_version,
        "trained_at": stamp.isoformat(),
        "architecture": "mobilenet_v3_small",
        "dataset": {
            "name": "Portadas de videojuegos",
            "source": "IGDB API (uso academico no comercial)",
            "manifest": str(args.manifest),
            "train_samples": len(train_frame),
            "val_samples": len(val_frame),
            "test_samples": len(test_frame),
            "classes": GAME_LABELS,
            "classes_es": GAME_LABELS_ES,
            "class_counts": class_counts,
            "split_counts": split_counts,
            "note": (
                "Se excluye Misc del entrenamiento; se usa como fallback cuando "
                "la confianza es baja."
            ),
        },
        "preprocessing": {
            "image_size": args.image_size,
            "eval_resize": config.GAME_EVAL_RESIZE,
            "color": "RGB",
            "mean": config.IMAGENET_MEAN,
            "std": config.IMAGENET_STD,
            "tensor_layout": "NCHW",
        },
        "transfer_learning": {
            "backbone": "MobileNetV3-Small",
            "pretrained_weights": "ImageNet IMAGENET1K_V1",
            "strategy": (
                "backbone congelado + cabeza entrenada sobre caracteristicas"
                + (" + fine-tuning del ultimo bloque" if args.unfreeze_last_block else "")
            ),
            "feature_dim": int(train_features.shape[1]),
            "epochs": args.epochs,
            "augment_views": views,
            "best_epoch": best_epoch,
        },
        "test_accuracy": round(accuracy, 6),
        "test_top3_accuracy": round(top3_accuracy, 6),
        "macro_precision": round(report["macro avg"]["precision"], 6),
        "macro_recall": round(report["macro avg"]["recall"], 6),
        "macro_f1": round(report["macro avg"]["f1-score"], 6),
        "weighted_f1": round(report["weighted avg"]["f1-score"], 6),
        "calibration": {
            "temperature": round(temperature, 6),
            "val_ece": round(val_ece, 6),
            "test_ece": round(test_ece, 6),
        },
        "per_class": {
            label: {
                "precision": round(report[label]["precision"], 6),
                "recall": round(report[label]["recall"], 6),
                "f1": round(report[label]["f1-score"], 6),
                "support": int(report[label]["support"]),
            }
            for label in GAME_LABELS_ES
        },
        "confusion_matrix": matrix.tolist(),
        "history": history,
    }
    if finetune:
        metrics["finetune"] = finetune

    figures = {
        "confusion_matrix": "confusion_matrix.png",
        "training_curves": "training_curves.png",
        "sample_predictions": "sample_predictions.png",
    }
    save_confusion_matrix(matrix, figures_dir / figures["confusion_matrix"])
    save_curves(history, figures_dir / figures["training_curves"])
    save_sample_predictions(
        model,
        test_dataset,
        temperature,
        figures_dir / figures["sample_predictions"],
    )
    metrics["figures"] = {key: f"figures/{value}" for key, value in figures.items()}

    genre_profiles = {}
    if args.profiles.exists():
        genre_profiles = json.loads(args.profiles.read_text(encoding="utf-8"))

    checkpoint = {
        "state_dict": model.state_dict(),
        "classes": GAME_GENRES,
        "model_version": model_version,
        "architecture": "mobilenet_v3_small",
        "dataset": metrics["dataset"],
        "metrics": metrics,
        "image_size": args.image_size,
        "preprocessing": metrics["preprocessing"],
        "temperature": temperature,
        "genre_profiles": genre_profiles,
    }

    model_path = args.output_dir / "model.pt"
    classes_path = args.output_dir / "classes.json"
    metrics_path = args.output_dir / "metrics.json"
    torch.save(checkpoint, model_path)
    classes_path.write_text(
        json.dumps(GAME_GENRES, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metrics_path.write_text(
        json.dumps(jsonable(metrics), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nModelo guardado en:", model_path)
    print("Clases guardadas en:", classes_path)
    print("Metricas guardadas en:", metrics_path)
    print(f"Accuracy test: {accuracy:.4f}")
    print(f"Top-3 test: {top3_accuracy:.4f}")
    print(f"Macro F1 test: {metrics['macro_f1']:.4f}")
    print(f"Temperatura: {temperature:.3f}")
    print("Figuras en:", figures_dir)


if __name__ == "__main__":
    main()
