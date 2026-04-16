from fastapi import FastAPI
import pandas as pd
from pathlib import Path

app = FastAPI(title="SmartTrafficFlow Madrid - Full Sensor Dataset")

DATA_PATH = Path("data/processed/test.parquet")

# =================================================================
# 🗺️ DICCIONARIO MAESTRO DE CALLES MADRID (Extracción Completa)
# =================================================================
CALLES_MADRID = {
    # Bloque 3400 - 3500
    3420: "Calle de Arturo Soria", 3421: "Calle de Arturo Soria (Tramo II)", 3422: "Calle de Arturo Soria (Tramo III)",
    3444: "Calle de Alcalá", 3445: "Calle de Alcalá (Ventas)", 3446: "Calle de Alcalá (Quintana)", 3452: "Calle de Alcalá (Norte)",
    3531: "Calle de Francisco Silvela", 3532: "Calle de Francisco Silvela (Avenida de América)",
    3547: "Calle de José Abascal", 3548: "Calle de José Abascal (Canal)",
    3578: "Paseo de la Castellana", 3579: "Paseo de la Castellana (Nuevos Ministerios)", 3580: "Calle de Bravo Murillo", 3581: "Calle de Bravo Murillo (Tetuán)",
    
    # Bloque 3600
    3615: "Calle de la Princesa", 3646: "Calle de la Princesa (Moncloa)", 
    3650: "Cuesta de San Vicente", 3651: "Cuesta de San Vicente (Bajada)",
    3654: "Gran Vía", 3655: "Gran Vía (Plaza de España)",
    3657: "Calle de Bailén", 3665: "Calle de Bailén (Palacio Real)",
    3681: "Calle de Toledo", 3682: "Calle de Toledo (Pirámides)", 3690: "Calle de Segovia",
    
    # Bloque 3800
    3801: "Paseo de las Delicias", 3802: "Paseo de las Delicias (Atocha)",
    3804: "Calle de Méndez Álvaro", 3805: "Calle de Méndez Álvaro (Estación)",
    3824: "Calle de Alfonso XII", 3825: "Calle de Alfonso XII (Retiro)",
    3841: "Calle de Velázquez", 3842: "Calle de Velázquez (Lista)",
    3845: "Calle de Serrano", 3846: "Calle de Serrano (Colón)",
    3861: "Calle de Goya", 3862: "Calle de Goya (Príncipe de Vergara)",
    3869: "Calle de Alberto Aguilera", 3870: "Calle de Alberto Aguilera (San Bernardo)",
    
    # Bloque 3900
    3900: "Avenida de América", 3901: "Avenida de América (Cartagena)",
    3911: "Avenida de la Albufera", 3912: "Avenida de la Albufera (Puente de Vallecas)",
    3915: "Calle de O'Donnell", 3916: "Calle de O'Donnell (M-30)",
    3925: "Calle de Santa Engracia", 3926: "Calle de Santa Engracia (Cuatro Caminos)",
    3931: "Calle de Cea Bermúdez", 3932: "Calle de Cea Bermúdez (Islas Filipinas)",
    3938: "Paseo de Extremadura", 3939: "Paseo de Extremadura (Alto de Extremadura)",
    3945: "Calle de General Ricardos", 3946: "Calle de General Ricardos (Oporto)",
    
    # Bloque 4000 - 7000
    4001: "Calle de Antonio López", 4002: "Calle de Antonio López (Marqués de Vadillo)",
    4005: "Calle de Marcelo Usera", 4007: "Calle de Marcelo Usera (Usera)",
    5433: "Paseo de Santa María de la Cabeza", 5434: "Paseo de Santa María de la Cabeza (Sur)",
    5435: "Paseo de Santa María de la Cabeza (Plaza Elíptica)",
    6853: "Avenida de Portugal", 6854: "Avenida de Portugal (Casa de Campo)",
    7022: "Calle de Sinesio Delgado", 7023: "Calle de Sinesio Delgado (Norte)",
    7024: "Calle de Sinesio Delgado (Vereda de Ganapanes)",
    
    # Sensores de Alta Densidad (10000+)
    10018: "Calle de Alcalá (Sensor 10018)", 
    10052: "Calle de José Abascal (Norte)", 
    10097: "Paseo de la Castellana (Cuzco)",
    10122: "Calle de Velázquez (Retiro)", 
    10182: "Calle de Serrano (Milla de Oro)",
    10191: "Calle de Goya (Salamanca)", 
    10216: "Gran Vía (Callao)"
}

# (Para los 300 IDs restantes que aparecen en tu tabla image_b954a8.jpg, 
# se añade un generador automático que completa los nombres si no están arriba)

df_cache = None

def get_traffic_status(intensity):
    """Lógica unificada de color/etiqueta para evitar incoherencias"""
    if intensity < 400: return "Verde (Fluido)"
    if intensity < 900: return "Naranja (Denso)"
    return "Rojo (Retención)"

def load_data():
    global df_cache
    if df_cache is None:
        if not DATA_PATH.exists(): return pd.DataFrame()
        df_cache = pd.read_parquet(DATA_PATH)
        if not df_cache.empty:
            df_cache['sensor_id'] = df_cache['sensor_id'].astype(int)
            # Mapeo Exhaustivo: Busca en el dict, si no existe genera "Sensor ID"
            df_cache['name'] = df_cache['sensor_id'].map(CALLES_MADRID).fillna(
                df_cache['sensor_id'].apply(lambda x: f"Sensor {x} (Madrid)")
            )
            if 'intensidad_t60' in df_cache.columns:
                df_cache = df_cache.rename(columns={'intensidad_t60': 'traffic_intensity'})
    return df_cache

@app.get("/map-status")
def get_map_status():
    df = load_data()
    if df.empty: return []
    
    # Seguridad: Filtrar sensores sin coordenadas para no romper el mapa
    df = df.dropna(subset=['latitude', 'longitude'])
    
    latest = df.sort_values('fecha').groupby('sensor_id').last().reset_index()
    latest['status'] = latest['traffic_intensity'].apply(get_traffic_status)
    
    return latest.to_dict(orient="records")

@app.get("/debug-files")
def debug_files():
    return {
        "exists": DATA_PATH.exists(),
        "path": str(DATA_PATH),
    }