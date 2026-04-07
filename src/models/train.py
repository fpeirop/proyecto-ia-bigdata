"""
src/models/train.py
-------------------
Entrenamiento del modelo predictivo SmartTrafficFlow AI.
Incluye: MLflow Tracking, Scikit-learn Pipelines y Explicabilidad con SHAP.
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
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

# Cargar variables de entorno y configurar logging
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Rutas
PROCESSED_PATH = Path(os.getenv("DATA_PROCESSED_PATH", "data/processed/"))
MODEL_PATH     = Path(os.getenv("MODEL_OUTPUT_PATH",   "models/"))
REPORTS_PATH   = Path("reports")
REPORTS_PATH.mkdir(exist_ok=True)

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

def generar_explicabilidad_shap(pipe, X_test, nombre_modelo):
    """Genera y guarda el gráfico SHAP para el modelo."""
    try:
        import shap
        logger.info(f"  Generando explicabilidad SHAP para {nombre_modelo}...")
        
        # Extraemos el modelo y el escalador del pipeline
        model_inst = pipe.named_steps['modelo']
        X_test_scaled = pipe.named_steps['scaler'].transform(X_test)
        
        # SHAP Summary Plot
        explainer = shap.TreeExplainer(model_inst)
        shap_values = explainer.shap_values(X_test_scaled)
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_test_scaled, feature_names=X_test.columns, show=False)
        plt.title(f"Importancia de Variables (SHAP) - {nombre_modelo}")
        
        plot_filename = f"shap_summary_{nombre_modelo.lower()}.png"
        plot_path = REPORTS_PATH / plot_filename
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        
        # Registrar en MLflow
        mlflow.log_artifact(str(plot_path))
        logger.info(f"  [OK] Gráfico SHAP guardado en: {plot_path}")
    except Exception as e:
        logger.warning(f"  [!] No se pudo generar SHAP: {e}")

def entrenar(nombre, estimador, X_train, y_train, X_test, y_test, target_col):
    logger.info(f"\nEntrenando: {nombre}...")
    with mlflow.start_run(run_name=nombre):
        # Pipeline: Escalado + Modelo (Evita Data Leakage)
        pipe = Pipeline([("scaler", StandardScaler()), ("modelo", estimador)])
        pipe.fit(X_train, y_train)
        
        y_pred = pipe.predict(X_test)
        m = metricas(y_test.values, y_pred)
        
        # Logging MLflow
        mlflow.log_params(estimador.get_params())
        mlflow.log_metrics(m)
        mlflow.log_param("target_col", target_col)
        mlflow.log_param("n_features", X_train.shape[1])
        mlflow.log_param("n_train",    len(X_train))
        mlflow.sklearn.log_model(pipe, artifact_path="model")
        
        # Explicabilidad (Solo para XGBoost o el mejor modelo para no ralentizar todo)
        if "XGBoost" in nombre:
            generar_explicabilidad_shap(pipe, X_test, nombre)
            
        logger.info(f"  MAE={m['MAE']:.2f} veh/h | RMSE={m['RMSE']:.2f} | R2={m['R2']:.4f}")
    return {"nombre": nombre, "pipeline": pipe, "metricas": m}

def ejecutar_entrenamiento():
    logger.info("=" * 55)
    logger.info("SMARTTRAFFICFLOW AI - ENTRENAMIENTO ML")
    logger.info("=" * 55)
    
    # Configurar MLflow
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "smarttrafficflow_mtd"))

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

    # Comparativa Final
    logger.info("\n" + "-"*55)
    logger.info("COMPARATIVA FINAL")
    for r in resultados:
        logger.info(f"  {r['nombre']:30s} MAE={r['metricas']['MAE']:8.2f}  R2={r['metricas']['R2']:.4f}")

    mejor = min(resultados, key=lambda r: r["metricas"]["MAE"])
    logger.info(f"\nMejor Modelo: {mejor['nombre']} | MAE={mejor['metricas']['MAE']:.2f}")

    # Serialización Final con Joblib
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d")
    slug  = mejor["nombre"].lower().replace(" ","_")
    hor   = target_col.replace("intensidad_","")
    
    # Nombre de archivo siguiendo recomendación (v1 + fecha)
    ruta_final = MODEL_PATH / f"{slug}_v1_{fecha}.pkl"
    joblib.dump(mejor["pipeline"], ruta_final)
    
    # Guardar metadatos de columnas
    (MODEL_PATH / "feature_cols.txt").write_text("\n".join(feat_cols), encoding="utf-8")
    (MODEL_PATH / "target_col.txt").write_text(target_col, encoding="utf-8")
    
    logger.info(f"Modelo guardado en: {ruta_final}")
    logger.info("=" * 55)
    logger.info("PROCESO COMPLETADO")
    logger.info("Para ver resultados: mlflow ui")
    logger.info("=" * 55)
    return ruta_final

if __name__ == "__main__":
    ejecutar_entrenamiento()