import numpy as np
import pandas as pd

def aplicar_ingenieria(df):
    """
    Transforma los datos crudos en señales matemáticas para la IA.
    """
    df = df.copy()
    
    # 1. CICLICIDAD DE LA HORA (Seno/Coseno)
    # Esto ayuda a la IA a entender que las 23:30 y las 00:00 están cerca
    df['hora'] = df.index.hour
    df['hour_sin'] = np.sin(2 * np.pi * df['hora'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hora'] / 24)
    
    # 2. LAGS (Memoria del sistema)
    # ¿Qué pasaba hace 30 y 60 minutos?
    for col in ['intensidad', 'ocupacion']:
        df[f'{col}_lag_1'] = df[col].shift(1)
        df[f'{col}_lag_2'] = df[col].shift(2)
    
    # 3. ROLLING STATS (Tendencia reciente)
    # Media móvil de las últimas 3 horas (6 periodos de 30min)
    df['intensidad_media_3h'] = df['intensidad'].rolling(window=6).mean()
    df['ocupacion_media_3h'] = df['ocupacion'].rolling(window=6).mean()
    
    # 4. LIMPIEZA
    # Al calcular lags y medias móviles, las primeras filas quedan con NaN
    return df.dropna()