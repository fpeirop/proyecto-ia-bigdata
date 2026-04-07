"""
src/models/predict.py
---------------------
Script de inferencia para SmartTrafficFlow AI.
Carga el modelo .pkl más reciente y genera predicciones sobre el set de test.
"""

import logging
import os
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv

# Configuración básica
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Rutas del proyecto
PROCESSED_PATH = Path(os.getenv("DATA_PROCESSED_PATH", "data/processed/"))
MODEL_PATH     = Path(os.getenv("MODEL_OUTPUT_PATH",   "models/"))
PRED_PATH      = Path("data/predictions/")
PRED_PATH.mkdir(parents=True, exist_ok=True)

def obtener_ultimo_modelo():
    """Identifica el archivo de modelo más reciente en la carpeta models/."""
    modelos = list(MODEL_PATH.glob("*.pkl"))
    if not modelos:
        raise FileNotFoundError(f"No se encontraron modelos .pkl en {MODEL_PATH}")
    
    # Selecciona el modelo con la fecha de modificación más reciente
    ultimo_modelo = max(modelos, key=os.path.getmtime)
    logger.info(f"Modelo seleccionado para inferencia: {ultimo_modelo.name}")
    return ultimo_modelo

def ejecutar_prediccion():
    logger.info("=" * 55)
    logger.info("SMARTTRAFFICFLOW AI - SISTEMA DE PREDICCIÓN")
    logger.info("=" * 55)

    # 1. Cargar el Pipeline y metadatos de columnas
    ruta_modelo = obtener_ultimo_modelo()
    pipeline = joblib.load(ruta_modelo)
    
    # Cargamos las columnas que el modelo espera (guardadas durante el entrenamiento)
    feat_file = MODEL_PATH / "feature_cols.txt"
    target_file = MODEL_PATH / "target_col.txt"
    
    if not feat_file.exists() or not target_file.exists():
        logger.error("Faltan archivos de metadatos en /models. ¿Has entrenado el modelo?")
        return
    
    cols_modelo = feat_file.read_text(encoding="utf-8").splitlines()
    target_col  = target_file.read_text(encoding="utf-8").strip()

    # 2. Cargar datos de prueba (t+30 o t+60)
    test_path = PROCESSED_PATH / "test.parquet"
    if not test_path.exists():
        logger.error("No se encuentra test.parquet en data/processed/")
        return
    
    df_test = pd.read_parquet(test_path)
    X_test = df_test[cols_modelo]
    y_real = df_test[target_col]

    # 3. Generar Predicciones
    logger.info(f"Generando predicciones para {len(X_test):,} registros...")
    preds = pipeline.predict(X_test)

    # 4. Consolidar resultados para el Frontend
    # Mantenemos sensor, fecha, valor real y añadimos la predicción
    resultados = df_test[['sensor_id', 'fecha', target_col]].copy()
    resultados['prediccion'] = preds.round(2)
    resultados['diferencia_abs'] = (resultados[target_col] - resultados['prediccion']).abs()

    # Guardar en CSV para que el Frontend lo cargue rápido
    ruta_salida = PRED_PATH / "ultimas_predicciones.csv"
    resultados.to_csv(ruta_salida, index=False)
    
    logger.info(f"Predicciones guardadas exitosamente en: {ruta_salida}")
    
    # 5. Reporte rápido de precisión en inferencia
    mae = resultados['diferencia_abs'].mean()
    logger.info(f"Precisión media (MAE) en estos datos: {mae:.2f} veh/h")
    logger.info("=" * 55)

if __name__ == "__main__":
    try:
        ejecutar_prediccion()
    except Exception as e:
        logger.error(f"Error crítico en el proceso de predicción: {e}")