import numpy as np
import pandas as pd
import holidays

def aplicar_ingenieria(df):
    """
    Transforma datos crudos en variables de IA (Ciclicidad, Festivos y Lags).
    """
    df = df.copy()
    
    # A) CICLICIDAD (Requisito: Seno/Coseno)
    df['hora'] = df.index.hour
    df['hour_sin'] = np.sin(2 * np.pi * df['hora'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hora'] / 24)
    
    # B) FESTIVOS MADRID (Requisito: Calendario de Madrid)
    # Identifica días especiales donde el tráfico cambia radicalmente
    es_holidays = holidays.Spain(subdiv='MD')
    df['es_festivo'] = df.index.map(lambda x: x in es_holidays).astype(int)
    
    # C) LAGS Y ROLLING (Requisito: 30/60 min y 3h)
    for col in ['intensidad', 'ocupacion']:
        df[f'{col}_lag_1'] = df[col].shift(1)  # Hace 30 min
        df[f'{col}_lag_2'] = df[col].shift(2)  # Hace 60 min
        df[f'{col}_media_3h'] = df[col].rolling(window=6).mean()
    
    return df.dropna() 