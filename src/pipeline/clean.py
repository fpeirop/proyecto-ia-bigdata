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
