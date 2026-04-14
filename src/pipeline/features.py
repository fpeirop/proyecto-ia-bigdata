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
    ejecutar_features(horizonte_h=0.5)