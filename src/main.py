import pandas as pd
from pipeline.features import aplicar_ingenieria

def ejecutar_etl():
    print("🚀 Iniciando Pipeline de Big Data...")
    
    # Aquí simulamos la carga de datos. 
    # En el futuro, aquí leerás tus CSV de data/raw
    print("📥 Cargando datos de sensores...")
    
    # Simulamos un DataFrame con fechas y una columna 'intensidad'
    fechas = pd.date_range(start='2024-01-01', periods=10, freq='30min')
    df = pd.DataFrame({'intensidad': [100, 120, 150, 130, 110, 105, 90, 85, 95, 100]}, index=fechas)

    # Aplicamos la magia
    print("⚙️ Aplicando Feature Engineering (Ciclicidad y Lags)...")
    df_final = aplicar_ingenieria(df)
    
    # Guardamos en Parquet (Como recomendaste por velocidad)
    print("💾 Guardando en formato Parquet...")
    df_final.to_parquet('data/processed/datos_sensores.parquet')
    
    print("✅ ¡Pipeline completado! Archivo generado en data/processed/")

if __name__ == "__main__":
    ejecutar_etl()