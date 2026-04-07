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
