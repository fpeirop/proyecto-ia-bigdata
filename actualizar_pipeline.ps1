# ==============================================================================
# actualizar_pipeline.ps1
# Actualiza los ficheros del pipeline ETL y modelos con las columnas
# reales del MTD (MTD_complete_data.csv)
#
# Ejecutar desde la raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File actualizar_pipeline.ps1
# ==============================================================================

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  SmartTrafficFlow AI - Actualizando pipeline al MTD" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# Crear carpetas si no existen
@("src\pipeline","src\models","src\frontend","models","data\raw",
  "data\processed","data\predictions","data\samples","notebooks") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}

# ==============================================================================
# src/pipeline/ingest.py
# ==============================================================================
@'
"""
src/pipeline/ingest.py
----------------------
Paso 1 del pipeline ETL: carga del Madrid Traffic Dataset (MTD).

Columnas reales del dataset:
    id, date, longitude, latitude, traffic_intensity,
    day_type, wind, temperature, precipitation,
    original_point, closest_point, oneway, lanes,
    name, highway, maxspeed, length
"""

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_PATH       = Path(os.getenv("DATA_RAW_PATH",       "data/raw/"))
PROCESSED_PATH = Path(os.getenv("DATA_PROCESSED_PATH", "data/processed/"))

MTD_FILE = "MTD_complete_data.csv"

COLS_UTILES = [
    "id", "date", "longitude", "latitude",
    "traffic_intensity", "day_type",
    "wind", "temperature", "precipitation",
    "highway", "maxspeed", "lanes",
]

COORD_FACTOR = 1e14


def cargar_mtd(ruta_csv: Path) -> pd.DataFrame:
    logger.info(f"Cargando: {ruta_csv.name}")
    with open(ruta_csv, "r", encoding="utf-8", errors="ignore") as f:
        primera = f.readline()
    sep = ";" if primera.count(";") > primera.count(",") else ","

    df = pd.read_csv(ruta_csv, sep=sep, low_memory=False,
                     encoding="utf-8", errors="replace")
    logger.info(f"  Filas: {len(df):,} | Columnas: {len(df.columns)}")

    cols_presentes = [c for c in COLS_UTILES if c in df.columns]
    df = df[cols_presentes].copy()

    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    for col in ["longitude", "latitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / COORD_FACTOR

    df["traffic_intensity"] = pd.to_numeric(df["traffic_intensity"], errors="coerce")

    for col in ["wind", "temperature", "precipitation", "maxspeed", "lanes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.rename(columns={"id": "sensor_id", "date": "fecha",
                             "traffic_intensity": "intensidad"})

    logger.info(f"  Columnas finales: {list(df.columns)}")
    logger.info(f"  Rango fechas: {df['fecha'].min()} -> {df['fecha'].max()}")
    logger.info(f"  Sensores unicos: {df['sensor_id'].nunique():,}")
    return df


def guardar_parquet(df: pd.DataFrame, nombre: str) -> Path:
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    destino = PROCESSED_PATH / f"{nombre}.parquet"
    df.to_parquet(destino, index=False, compression="snappy")
    logger.info(f"  Guardado: {destino} ({destino.stat().st_size/1024:.0f} KB)")
    return destino


def ejecutar_ingesta() -> dict:
    logger.info("=" * 55)
    logger.info("PASO 1 - INGESTA DE DATOS (MTD)")
    logger.info("=" * 55)

    ruta = RAW_PATH / MTD_FILE
    if not ruta.exists():
        csvs = list(RAW_PATH.glob("*.csv"))
        if not csvs:
            logger.error(f"No se encontro {MTD_FILE} en {RAW_PATH}")
            return {}
        ruta = csvs[0]
        logger.warning(f"Usando: {ruta.name}")

    df = cargar_mtd(ruta)
    destino = guardar_parquet(df, "trafico_raw")
    logger.info("INGESTA COMPLETADA")
    return {"trafico_raw": destino}


if __name__ == "__main__":
    ejecutar_ingesta()
'@ | Set-Content -Encoding UTF8 "src\pipeline\ingest.py"
Write-Host "[OK] src/pipeline/ingest.py" -ForegroundColor Green

# ==============================================================================
# src/pipeline/clean.py
# ==============================================================================
@'
"""
src/pipeline/clean.py
---------------------
Paso 2 del pipeline ETL: limpieza y validacion adaptada al MTD real.

Problemas detectados:
  - traffic_intensity con valores extremos (6.23e+16) -> outliers
  - Coordenadas corregidas en ingest.py
  - Posibles nulos en variables climaticas
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_PATH = Path("data/processed/")
INTENSIDAD_MAX = 5_000
INTENSIDAD_MIN = 0


def limpiar_trafico(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Inicio limpieza - Filas: {len(df):,}")

    n = len(df)
    df = df.drop_duplicates(subset=["sensor_id", "fecha"])
    logger.info(f"  Duplicados eliminados: {n - len(df):,}")

    n = len(df)
    df = df.dropna(subset=["fecha"])
    logger.info(f"  Sin fecha valida eliminados: {n - len(df):,}")

    n = len(df)
    df = df[(df["intensidad"] >= INTENSIDAD_MIN) & (df["intensidad"] <= INTENSIDAD_MAX)]
    logger.info(f"  Outliers extremos eliminados: {n - len(df):,}")

    q1, q99 = df["intensidad"].quantile([0.01, 0.99])
    n = len(df)
    df = df[(df["intensidad"] >= q1) & (df["intensidad"] <= q99)]
    logger.info(f"  Outliers estadisticos eliminados: {n - len(df):,} (rango {q1:.1f}-{q99:.1f})")

    nulos = df["intensidad"].isna().sum()
    if nulos > 0:
        df = df.sort_values(["sensor_id", "fecha"])
        df["intensidad"] = (
            df.groupby("sensor_id")["intensidad"]
            .transform(lambda x: x.interpolate(method="linear", limit=3))
        )
        df["intensidad"] = df["intensidad"].fillna(df["intensidad"].median())
        logger.info(f"  Nulos en intensidad imputados: {nulos:,}")

    for col in ["wind", "temperature", "precipitation"]:
        if col in df.columns:
            nulos = df[col].isna().sum()
            if nulos > 0:
                df[col] = df[col].fillna(df[col].median())
                logger.info(f"  Nulos en '{col}' imputados: {nulos:,}")

    df["sensor_id"] = df["sensor_id"].astype(str)
    df["fecha"]     = pd.to_datetime(df["fecha"])
    df = df.sort_values(["sensor_id", "fecha"]).reset_index(drop=True)

    logger.info(f"Limpieza completada - Filas: {len(df):,} | Sensores: {df['sensor_id'].nunique():,}")
    return df


def validar_calidad(df: pd.DataFrame) -> bool:
    logger.info("Validando calidad...")
    ok = True
    for col in ["sensor_id", "fecha", "intensidad"]:
        if col in df.columns:
            nulos = df[col].isna().sum()
            if nulos > 0:
                logger.error(f"  FAIL: '{col}' tiene {nulos:,} nulos")
                ok = False
            else:
                logger.info(f"  OK: '{col}' sin nulos")
    fuera = ((df["intensidad"] < 0) | (df["intensidad"] > INTENSIDAD_MAX)).sum()
    if fuera > 0:
        logger.error(f"  FAIL: {fuera:,} valores fuera de rango")
        ok = False
    else:
        logger.info(f"  OK: intensidad en rango valido")
    logger.info(f"Validacion: {'PASADA' if ok else 'FALLIDA'}")
    return ok


def ejecutar_limpieza() -> dict:
    logger.info("=" * 55)
    logger.info("PASO 2 - LIMPIEZA Y VALIDACION")
    logger.info("=" * 55)
    ruta = PROCESSED_PATH / "trafico_raw.parquet"
    if not ruta.exists():
        logger.error("No se encontro trafico_raw.parquet.")
        return {}
    df = pd.read_parquet(ruta)
    df_limpio = limpiar_trafico(df)
    validar_calidad(df_limpio)
    destino = PROCESSED_PATH / "trafico_limpio.parquet"
    df_limpio.to_parquet(destino, index=False, compression="snappy")
    logger.info(f"Dataset limpio: {destino}")
    logger.info("LIMPIEZA COMPLETADA")
    return {"trafico_limpio": destino}


if __name__ == "__main__":
    ejecutar_limpieza()
'@ | Set-Content -Encoding UTF8 "src\pipeline\clean.py"
Write-Host "[OK] src/pipeline/clean.py" -ForegroundColor Green

# ==============================================================================
# src/pipeline/features.py
# ==============================================================================
@'
"""
src/pipeline/features.py
------------------------
Paso 3 del pipeline ETL: Feature Engineering completo para el MTD.

Frecuencia del dataset: 1 hora
Columnas disponibles: sensor_id, fecha, intensidad, latitude, longitude,
                      wind, temperature, precipitation, highway, maxspeed, lanes
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_PATH = Path("data/processed/")

FESTIVOS_MADRID = pd.to_datetime([
    "2022-01-01","2022-01-06","2022-04-15","2022-05-02","2022-05-15",
    "2022-10-12","2022-11-01","2022-11-09","2022-12-06","2022-12-08","2022-12-25",
    "2023-01-01","2023-01-06","2023-04-07","2023-05-02","2023-05-15",
    "2023-10-12","2023-11-01","2023-11-09","2023-12-06","2023-12-08","2023-12-25",
    "2024-01-01","2024-01-06","2024-03-29","2024-05-02","2024-05-15",
    "2024-10-12","2024-11-01","2024-11-11","2024-12-06","2024-12-09","2024-12-25",
])


def features_temporales(df):
    logger.info("  Generando features temporales...")
    df = df.copy()
    dt = df["fecha"]
    hora = dt.dt.hour + dt.dt.minute / 60
    df["hora_sin"] = np.sin(2 * np.pi * hora / 24)
    df["hora_cos"] = np.cos(2 * np.pi * hora / 24)
    dia = dt.dt.dayofweek
    df["dia_semana_sin"] = np.sin(2 * np.pi * dia / 7)
    df["dia_semana_cos"] = np.cos(2 * np.pi * dia / 7)
    mes = dt.dt.month
    df["mes_sin"] = np.sin(2 * np.pi * mes / 12)
    df["mes_cos"] = np.cos(2 * np.pi * mes / 12)
    df["hora"]       = dt.dt.hour
    df["dia_semana"] = dt.dt.dayofweek
    df["mes"]        = dt.dt.month
    df["es_finde"]   = (dt.dt.dayofweek >= 5).astype(int)
    df["es_festivo"] = dt.dt.normalize().isin(FESTIVOS_MADRID).astype(int)
    es_laboral = (dt.dt.dayofweek < 5) & (df["es_festivo"] == 0)
    df["hora_punta"] = (es_laboral & (dt.dt.hour.between(7,9) | dt.dt.hour.between(17,20))).astype(int)
    logger.info("    OK: hora_sin/cos, dia_sin/cos, mes_sin/cos, es_festivo, hora_punta")
    return df


def features_lag(df):
    logger.info("  Generando features lag y rolling (freq=1h)...")
    df = df.copy().sort_values(["sensor_id", "fecha"])
    grp = df.groupby("sensor_id")["intensidad"]
    df["intensidad_lag_1h"]   = grp.shift(1)
    df["intensidad_lag_2h"]   = grp.shift(2)
    df["intensidad_lag_24h"]  = grp.shift(24)
    df["intensidad_media_3h"] = grp.transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    df["intensidad_std_3h"]   = grp.transform(lambda x: x.shift(1).rolling(3, min_periods=1).std().fillna(0))
    df["intensidad_delta_1h"] = grp.shift(0) - grp.shift(1)
    logger.info("    OK: lag_1h, lag_2h, lag_24h, media_3h, std_3h, delta_1h")
    return df


def features_clima(df):
    logger.info("  Procesando features climaticas...")
    if "precipitation" in df.columns:
        df["llueve"]         = (df["precipitation"] > 0).astype(int)
        df["lluvia_intensa"] = (df["precipitation"] > 5).astype(int)
    if "temperature" in df.columns:
        df["temp_extrema"] = ((df["temperature"] > 35) | (df["temperature"] < 2)).astype(int)
    if "wind" in df.columns:
        df["viento_fuerte"] = (df["wind"] > 50).astype(int)
    logger.info("    OK: llueve, lluvia_intensa, temp_extrema, viento_fuerte")
    return df


def features_infraestructura(df):
    logger.info("  Codificando infraestructura viaria...")
    if "highway" in df.columns:
        jerarquia = {"motorway":6,"trunk":5,"primary":4,"secondary":3,
                     "tertiary":2,"residential":1,"unclassified":1,"service":0}
        df["highway_encoded"] = df["highway"].str.lower().map(jerarquia).fillna(1)
    for col in ["maxspeed", "lanes"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())
    logger.info("    OK: highway_encoded, maxspeed, lanes")
    return df


def generar_target(df, horizonte_h=1):
    logger.info(f"  Generando target t+{horizonte_h*60}min...")
    df = df.copy().sort_values(["sensor_id", "fecha"])
    col = f"intensidad_t{horizonte_h*60}"
    df[col] = df.groupby("sensor_id")["intensidad"].shift(-horizonte_h)
    logger.info(f"    OK: '{col}' generado")
    return df, col


def split_temporal(df, meses_test=3):
    corte = df["fecha"].max() - pd.DateOffset(months=meses_test)
    train = df[df["fecha"] <= corte].copy()
    test  = df[df["fecha"] >  corte].copy()
    logger.info(f"  Split - Corte: {corte.date()} | Train: {len(train):,} | Test: {len(test):,}")
    return train, test


def ejecutar_features(horizonte_h=1):
    logger.info("=" * 55)
    logger.info("PASO 3 - FEATURE ENGINEERING")
    logger.info("=" * 55)
    ruta = PROCESSED_PATH / "trafico_limpio.parquet"
    if not ruta.exists():
        logger.error("No se encontro trafico_limpio.parquet.")
        return {}
    df = pd.read_parquet(ruta)
    logger.info(f"Dataset: {len(df):,} filas | {df['sensor_id'].nunique()} sensores")
    df = features_temporales(df)
    df = features_lag(df)
    df = features_clima(df)
    df = features_infraestructura(df)
    df, col_target = generar_target(df, horizonte_h=horizonte_h)
    n = len(df)
    df = df.dropna(subset=["intensidad_lag_1h", "intensidad_lag_2h", col_target])
    logger.info(f"  Filas eliminadas por NaN: {n - len(df):,} | Features: {len(df.columns)}")
    train, test = split_temporal(df)
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    train.to_parquet(PROCESSED_PATH / "train.parquet",             index=False)
    test.to_parquet(PROCESSED_PATH  / "test.parquet",              index=False)
    df.to_parquet(PROCESSED_PATH    / "dataset_features.parquet",  index=False)
    (PROCESSED_PATH / "target_col.txt").write_text(col_target, encoding="utf-8")
    logger.info("Guardados: train.parquet, test.parquet, dataset_features.parquet")
    logger.info("FEATURE ENGINEERING COMPLETADO")
    return {"train": PROCESSED_PATH/"train.parquet", "test": PROCESSED_PATH/"test.parquet",
            "target_col": col_target}


if __name__ == "__main__":
    ejecutar_features(horizonte_h=1)
'@ | Set-Content -Encoding UTF8 "src\pipeline\features.py"
Write-Host "[OK] src/pipeline/features.py" -ForegroundColor Green

# ==============================================================================
# src/pipeline/run_pipeline.py
# ==============================================================================
@'
"""
src/pipeline/run_pipeline.py
Orquestador del pipeline ETL completo.
Uso: python src/pipeline/run_pipeline.py  |  make etl
"""
import importlib
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ejecutar_pipeline():
    t0 = time.time()
    logger.info("=" * 55)
    logger.info("SMARTTRAFFICFLOW AI - PIPELINE ETL COMPLETO")
    logger.info("=" * 55)
    pasos = [
        ("INGESTA",             "src.pipeline.ingest",   "ejecutar_ingesta"),
        ("LIMPIEZA",            "src.pipeline.clean",    "ejecutar_limpieza"),
        ("FEATURE ENGINEERING", "src.pipeline.features", "ejecutar_features"),
    ]
    for nombre, modulo, funcion in pasos:
        try:
            mod = importlib.import_module(modulo)
            getattr(mod, funcion)()
        except Exception as e:
            logger.error(f"Error en {nombre}: {e}")
            sys.exit(1)
    logger.info("=" * 55)
    logger.info(f"PIPELINE COMPLETADO en {time.time()-t0:.1f}s")
    logger.info("Datos listos en data/processed/")
    logger.info("=" * 55)


if __name__ == "__main__":
    ejecutar_pipeline()
'@ | Set-Content -Encoding UTF8 "src\pipeline\run_pipeline.py"
Write-Host "[OK] src/pipeline/run_pipeline.py" -ForegroundColor Green

# ==============================================================================
# src/models/train.py
# ==============================================================================
@'
"""
src/models/train.py
-------------------
Entrenamiento del modelo predictivo SmartTrafficFlow AI.
Target: intensidad_t60 (intensidad en t+60 minutos)
Uso: python src/models/train.py  |  make train
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_PATH = Path(os.getenv("DATA_PROCESSED_PATH", "data/processed/"))
MODEL_PATH     = Path(os.getenv("MODEL_OUTPUT_PATH",   "models/"))

FEATURE_COLS = [
    "hora_sin","hora_cos","dia_semana_sin","dia_semana_cos","mes_sin","mes_cos",
    "es_festivo","es_finde","hora_punta",
    "intensidad_lag_1h","intensidad_lag_2h","intensidad_lag_24h",
    "intensidad_media_3h","intensidad_std_3h","intensidad_delta_1h",
    "wind","temperature","precipitation",
    "llueve","lluvia_intensa","temp_extrema","viento_fuerte",
    "highway_encoded","maxspeed","lanes",
]


def cargar_datos():
    train = pd.read_parquet(PROCESSED_PATH / "train.parquet")
    test  = pd.read_parquet(PROCESSED_PATH / "test.parquet")
    tf = PROCESSED_PATH / "target_col.txt"
    target_col = tf.read_text(encoding="utf-8").strip() if tf.exists() else \
                 next(c for c in train.columns if c.startswith("intensidad_t"))
    logger.info(f"Target: '{target_col}' | Train: {len(train):,} | Test: {len(test):,}")
    return train, test, target_col


def preparar_xy(df, target_col):
    cols = [c for c in FEATURE_COLS if c in df.columns]
    miss = [c for c in FEATURE_COLS if c not in df.columns]
    if miss:
        logger.warning(f"  Features omitidas (no en dataset): {miss}")
    ok = df[cols + [target_col]].dropna()
    return ok[cols], ok[target_col], cols


def metricas(y_real, y_pred):
    return {
        "MAE":  round(float(mean_absolute_error(y_real, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_real, y_pred))), 4),
        "R2":   round(float(r2_score(y_real, y_pred)), 4),
    }


def entrenar(nombre, estimador, X_train, y_train, X_test, y_test, target_col):
    logger.info(f"\nEntrenando: {nombre}...")
    with mlflow.start_run(run_name=nombre):
        pipe = Pipeline([("scaler", StandardScaler()), ("modelo", estimador)])
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        m = metricas(y_test.values, y_pred)
        mlflow.log_params(estimador.get_params())
        mlflow.log_metrics(m)
        mlflow.log_param("target_col", target_col)
        mlflow.log_param("n_features", X_train.shape[1])
        mlflow.log_param("n_train",    len(X_train))
        mlflow.sklearn.log_model(pipe, artifact_path="model")
        logger.info(f"  MAE={m['MAE']:.2f} veh/h | RMSE={m['RMSE']:.2f} | R2={m['R2']:.4f}")
    return {"nombre": nombre, "pipeline": pipe, "metricas": m}


def ejecutar_entrenamiento():
    logger.info("=" * 55)
    logger.info("SMARTTRAFFICFLOW AI - ENTRENAMIENTO ML")
    logger.info("=" * 55)
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "mlruns/"))
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "smarttrafficflow"))

    train, test, target_col = cargar_datos()
    X_train, y_train, feat_cols = preparar_xy(train, target_col)
    X_test,  y_test,  _         = preparar_xy(test,  target_col)
    logger.info(f"\nFeatures usadas ({len(feat_cols)}): {feat_cols}")

    modelos = {
        "RandomForest_baseline": RandomForestRegressor(
            n_estimators=100, max_depth=12, min_samples_leaf=5,
            min_samples_split=10, random_state=42, n_jobs=-1),
        "XGBoost_optimizado": XGBRegressor(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            reg_alpha=0.1, reg_lambda=1.0, random_state=42,
            n_jobs=-1, verbosity=0),
    }

    resultados = [entrenar(n, e, X_train, y_train, X_test, y_test, target_col)
                  for n, e in modelos.items()]

    logger.info("\n" + "-"*55)
    logger.info("COMPARATIVA")
    for r in resultados:
        logger.info(f"  {r['nombre']:35s} MAE={r['metricas']['MAE']:6.2f}  R2={r['metricas']['R2']:.4f}")

    mejor = min(resultados, key=lambda r: r["metricas"]["MAE"])
    logger.info(f"\nMejor: {mejor['nombre']} | MAE={mejor['metricas']['MAE']:.2f}")

    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d")
    slug  = mejor["nombre"].lower().replace(" ","_")
    hor   = target_col.replace("intensidad_","")
    ruta  = MODEL_PATH / f"{slug}_{hor}_{fecha}.pkl"
    joblib.dump(mejor["pipeline"], ruta)
    (MODEL_PATH / "feature_cols.txt").write_text("\n".join(feat_cols), encoding="utf-8")
    (MODEL_PATH / "target_col.txt").write_text(target_col, encoding="utf-8")
    logger.info(f"Modelo: {ruta}")
    logger.info("=" * 55)
    logger.info("ENTRENAMIENTO COMPLETADO")
    logger.info("mlflow ui -> http://localhost:5000")
    logger.info("=" * 55)
    return ruta


if __name__ == "__main__":
    ejecutar_entrenamiento()
'@ | Set-Content -Encoding UTF8 "src\models\train.py"
Write-Host "[OK] src/models/train.py" -ForegroundColor Green

# ==============================================================================
# Resumen
# ==============================================================================
Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  ACTUALIZACION COMPLETADA" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Ficheros actualizados al MTD real:" -ForegroundColor White
Write-Host "    src/pipeline/ingest.py   <- lee MTD_complete_data.csv"
Write-Host "    src/pipeline/clean.py    <- elimina outliers extremos"
Write-Host "    src/pipeline/features.py <- usa wind, temperature, precipitation"
Write-Host "    src/pipeline/run_pipeline.py"
Write-Host "    src/models/train.py      <- 25 features, MLflow, XGBoost"
Write-Host ""
Write-Host "  Siguientes pasos:" -ForegroundColor Yellow
Write-Host "    1. Asegurate de que MTD_complete_data.csv esta en data/raw/"
Write-Host "    2. pip install -r environment/requirements.txt"
Write-Host "    3. make etl"
Write-Host "    4. make train"
Write-Host "    5. make predict"
Write-Host "    6. make app"
Write-Host ""
