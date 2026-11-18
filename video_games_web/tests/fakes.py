"""Dobles de prueba para la API externa."""

MODEL_VERSION = "test-2026"


class FakeApiClient:
    def __init__(self):
        self.model_version = MODEL_VERSION
        self.info = {
            "model_version": MODEL_VERSION,
            "target": "global_sales",
            "target_transform": "log1p",
            "n_train": 100,
            "n_features": 10,
            "metrics": {
                "train": {"R2": 0.26, "RMSE_log": 0.33, "MAE_log": 0.22},
                "test": {"R2": 0.24, "RMSE_log": 0.35, "MAE_log": 0.22},
            },
            "reference_levels": {"platform": "PS2"},
            "allowed_platforms": ["PS2", "PS4", "Wii"],
            "allowed_genres": ["Action", "Sports", "Racing"],
            "year_range": [1980, 2020],
            "excluded_columns": ["rank"],
            "disclaimer": "Prediccion aproximada.",
        }
        self.health_data = {"status": "ok", "model_version": MODEL_VERSION}
        self.predict_calls: list[dict] = []
        self.predict_error = None
        self.health_error = None
        self.info_error = None

    def health(self):
        if self.health_error:
            raise self.health_error
        return self.health_data

    def model_info(self, force=False):
        if self.info_error:
            raise self.info_error
        return self.info

    def predict(self, game):
        if self.predict_error:
            raise self.predict_error
        self.predict_calls.append(game)
        return {
            "prediction": {
                "predicted_sales_millions": 0.6827,
                "predicted_log_sales": 0.5204,
                "interval_95_millions": [0.0, 2.2618],
                "warnings": [],
            },
            "model_version": self.model_version,
        }


class FakeVisionClient:
    def __init__(self):
        self.model_version = "vision-test-2026"
        self.info = {
            "model_version": self.model_version,
            "architecture": "mobilenet_v3_small",
            "dataset": {"name": "CIFAR-10"},
            "image_size": 160,
            "num_classes": 10,
            "classes": [{"id": 3, "label": "cat", "label_es": "gato"}],
            "metrics": {"test_accuracy": 0.886},
            "preprocessing": {"resize": [160, 160]},
            "disclaimer": "Clasificacion aproximada.",
        }
        self.health_data = {"status": "ok", "model_version": self.model_version}
        self.predict_calls: list[dict] = []
        self.predict_error = None
        self.health_error = None
        self.info_error = None

    def health(self):
        if self.health_error:
            raise self.health_error
        return self.health_data

    def model_info(self, force=False):
        if self.info_error:
            raise self.info_error
        return self.info

    def predict_image(self, image_bytes, filename, content_type, top_k=3):
        if self.predict_error:
            raise self.predict_error
        self.predict_calls.append(
            {
                "bytes": image_bytes,
                "filename": filename,
                "content_type": content_type,
                "top_k": top_k,
            }
        )
        return {
            "prediction": {
                "label": "cat",
                "label_es": "gato",
                "confidence": 0.9123,
                "top_k": [
                    {
                        "class_id": 3,
                        "label": "cat",
                        "label_es": "gato",
                        "confidence": 0.9123,
                    },
                    {
                        "class_id": 5,
                        "label": "dog",
                        "label_es": "perro",
                        "confidence": 0.0412,
                    },
                    {
                        "class_id": 4,
                        "label": "deer",
                        "label_es": "ciervo",
                        "confidence": 0.0121,
                    },
                ],
                "latency_ms": 12.5,
            },
            "model_version": self.model_version,
            "request_id": "vision-req-1",
        }
