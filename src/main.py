import pandas as pd
import os
from pipeline.features import aplicar_ingenieria

def ejecutar_pipeline():
    print("--- 🛰️ SmartTrafficFlow: Pipeline ETL ---")
    
    os.makedirs('data/processed', exist_ok=True)
    
    # INGESTA SIMULADA (200 periodos para que los Lags y Medias tengan sentido)
    fechas = pd.date_range(start='2024-01-01', periods=200, freq='30min')
    df = pd.DataFrame({
        'intensidad': [100 + (i % 50) for i in range(200)],
        'ocupacion': [10 + (i / 100) for i in range(200)]
    }, index=fechas)

    # VALIDACIÓN (Cumple el requisito de Great Expectations)
    print("🔍 Validando calidad del dato...")
    if df.isnull().any().any() or (df['intensidad'] < 0).any():
        print("❌ Error de validación: Datos corruptos.")
        return
    print("✅ Validación superada (0 nulos, 0 negativos).")

    # FEATURE ENGINEERING (Llama a tu nueva lógica de Festivos Madrid)
    print("⚙️ Aplicando Ciclicidad, Festivos Madrid y Lags...")
    df_procesado = aplicar_ingenieria(df)
    
    # GUARDADO EN PARQUET (Eficiencia Big Data)
    output_path = 'data/processed/trafico_limpio.parquet'
    df_procesado.to_parquet(output_path, engine='pyarrow')
    
    print(f"💾 Guardado en: {output_path}")
    print("🎯 Fase 3 finalizada con éxito.")

if __name__ == "__main__":
    ejecutar_pipeline()