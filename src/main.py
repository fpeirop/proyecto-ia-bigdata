import pandas as pd
import os
from pipeline.features import aplicar_ingenieria

def ejecutar_pipeline():
    print("--- 🛰️ SmartTrafficFlow: Iniciando Pipeline ETL ---")
    
    # 1. Creación de rutas (Evita errores de "Carpeta no encontrada")
    os.makedirs('data/processed', exist_ok=True)
    
    # 2. INGESTA (Simulada con volumen suficiente para Feature Engineering)
    print("📥 Cargando datos de sensores (Simulación)...")
    fechas = pd.date_range(start='2024-01-01', periods=100, freq='30min')
    df = pd.DataFrame({
        'intensidad': [100 + i for i in range(100)],
        'ocupacion': [10 + (i/10) for i in range(100)]
    }, index=fechas)
    
    # 3. FEATURE ENGINEERING
    print("⚙️ Generando variables (Seno/Coseno, Lags, Medias móviles)...")
    df_procesado = aplicar_ingenieria(df)
    
    # 4. GUARDADO EN PARQUET (Eficiencia máxima)
    output_path = 'data/processed/trafico_limpio.parquet'
    df_procesado.to_parquet(output_path, engine='pyarrow')
    
    print(f"💾 Dataset procesado guardado en: {output_path}")
    print("✅ Pipeline completado con éxito.")

if __name__ == "__main__":
    ejecutar_pipeline()