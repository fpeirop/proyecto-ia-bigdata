import numpy as np
import pandas as pd

def aplicar_ingenieria(df):
    """Crea las variables para el modelo de IA"""
    # 1. Ciclicidad de la hora
    df['hora'] = df.index.hour
    df['hour_sin'] = np.sin(2 * np.pi * df['hora'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hora'] / 24)
    
    # 2. Lags (Lo que pasó hace 30 y 60 min)
    df['intensidad_lag_1'] = df['intensidad'].shift(1)
    df['intensidad_lag_2'] = df['intensidad'].shift(2)
    
    # 3. Media móvil (Últimas 3 horas)
    df['media_3h'] = df['intensidad'].rolling(window=6).mean()
    
    return df.dropna()