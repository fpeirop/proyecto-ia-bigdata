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

    df = pd.read_csv(
        ruta_csv, 
        sep=sep, 
        low_memory=False,
        encoding="utf-8", 
        on_bad_lines="skip"  # Sustituimos errors="replace" por esto
    )
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
