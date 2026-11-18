"""Etiquetas de CIFAR-10 en ingles y espanol."""

CIFAR10_CLASSES = [
    {"id": 0, "label": "airplane", "label_es": "avion"},
    {"id": 1, "label": "automobile", "label_es": "automovil"},
    {"id": 2, "label": "bird", "label_es": "pajaro"},
    {"id": 3, "label": "cat", "label_es": "gato"},
    {"id": 4, "label": "deer", "label_es": "ciervo"},
    {"id": 5, "label": "dog", "label_es": "perro"},
    {"id": 6, "label": "frog", "label_es": "rana"},
    {"id": 7, "label": "horse", "label_es": "caballo"},
    {"id": 8, "label": "ship", "label_es": "barco"},
    {"id": 9, "label": "truck", "label_es": "camion"},
]

CIFAR10_LABELS = [item["label"] for item in CIFAR10_CLASSES]
CIFAR10_LABELS_ES = [item["label_es"] for item in CIFAR10_CLASSES]
