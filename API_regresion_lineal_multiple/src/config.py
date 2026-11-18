"""Configuracion central del proyecto.

Todo lo que se puede ajustar sin tocar la logica vive aqui.
"""

from pathlib import Path

# Rutas
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "video_games_sales.csv"
OUTPUT_DIR = ROOT / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
ARTIFACT_PATH = ROOT / "artifacts" / "model.joblib"
METADATA_PATH = ROOT / "artifacts" / "metadata.json"

# Variable objetivo y su transformacion
TARGET = "global_sales"
TARGET_LOG = "log_global_sales"

# Columnas que nunca entran como predictoras:
#   rank  -> orden por ventas (fuga de informacion)
#   name  -> identificador
#   *_sales regionales -> suman exactamente la variable objetivo (colinealidad perfecta)
DROP_COLUMNS = ["rank", "name", "na_sales", "eu_sales", "jp_sales", "other_sales"]

# Predictoras
NUMERIC_FEATURES = ["year"]
CATEGORICAL_FEATURES = ["platform", "genre", "publisher"]

# Preprocesamiento
TOP_PUBLISHERS = 30  # el resto se agrupa como "Other"
TEST_SIZE = 0.20
RANDOM_STATE = 42
ALPHA = 0.05  # nivel de significancia para los contrastes
