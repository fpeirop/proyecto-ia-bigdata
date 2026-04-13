import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# Configuración de URL
API_URL = "http://localhost:8000"

st.set_page_config(layout="wide", page_title="Smart Traffic Madrid", page_icon="🚦")

# Refresco automático cada 30 segundos
count = st_autorefresh(interval=30000, limit=None, key="traffic_counter")

def fetch_api(endpoint):
    try:
        res = requests.get(f"{API_URL}/{endpoint}", timeout=5)
        if res.status_code == 200: 
            return res.json()
    except Exception:
        return None
    return None

st.title("🚦 Smart Traffic Madrid - IA de Predicción")
if count > 0:
    st.caption(f"🔄 Última actualización en tiempo real (Refresco nº: {count})")

# 1. CARGA DE DATOS
map_data_raw = fetch_api("map-status")

if map_data_raw:
    df_map = pd.DataFrame(map_data_raw)
    df_map['name'] = df_map['name'].astype(str)
    
    opciones = ["Ver Mapa General"] + sorted(df_map['name'].unique().tolist())
    calle_sel = st.selectbox("📍 Selecciona una ubicación o calle:", opciones)
    
    # --- LÓGICA DE POSICIONAMIENTO ---
    if calle_sel == "Ver Mapa General":
        display_df = df_map
        zoom_level = 11.0
        center_map = {"lat": 40.4167, "lon": -3.7033}
    else:
        display_df = df_map[df_map['name'] == calle_sel]
        # Fix de coordenadas para Calle de Bailén
        lat_real, lon_real = (40.4145, -3.7135) if "Bailén" in calle_sel else (display_df.iloc[0]['latitude'], display_df.iloc[0]['longitude'])
        zoom_level = 16.5
        center_map = {"lat": lat_real, "lon": lon_real}

    # --- MAPA ---
    fig_map = px.scatter_mapbox(
        display_df, lat="latitude", lon="longitude", color="status",
        color_discrete_map={"Verde (Fluido)": "#28a745", "Naranja (Denso)": "#ff8c00", "Rojo (Retención)": "#ff0000"},
        center=center_map, zoom=zoom_level, height=550
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # --- ANÁLISIS TÉCNICO AVANZADO ---
    if calle_sel != "Ver Mapa General" and not display_df.empty:
        info = display_df.iloc[0]
        st.markdown("---")
        st.subheader(f"📊 Gestión de Movilidad e Infraestructura: {calle_sel}")

        # 1. MOTOR DE VALIDACIÓN (Lógica para corregir anomalías)
        nombre_calle = calle_sel.lower()
        v_sensor = info.get('maxspeed', 50)
        # Identificamos si es centro histórico o arteria principal
        es_urbana = any(k in nombre_calle for k in ["calle", "bailén", "mayor", "plaza", "avenida", "paseo", "gran vía"])
        
        # Corrección de Velocidad (Blindaje contra errores de 100 km/h en ciudad)
        v_legal = 50.0 if (es_urbana and v_sensor > 50) else v_sensor
        error_sensor = (es_urbana and v_sensor > 50)

        # Validación de Calendario (Sincronización con fecha sistema)
        es_finde_real = datetime.now().weekday() >= 5 
        contexto_validado = "Laborable" if not es_finde_real else "Festivo / Fin de Semana"

        # 2. PANEL DE KPIs (Métricas de Operación)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Intensidad Actual", f"{int(info['traffic_intensity'])} veh/h")
        c2.metric("Estado del Flujo", info['status']) 
        c3.metric("Límite Normativo", f"{int(v_legal)} km/h") 
        c4.metric("Capacidad Vía", f"{int(info.get('lanes', 0))} Carriles")

        st.markdown("---")
        
        # 3. ATRIBUTOS PROFESIONALES DE LA VÍA
        col_inf, col_met = st.columns(2)
        
        with col_inf:
            st.markdown("### 🏗️ Atributos de Infraestructura")
            tipo_via = "Arteria Urbana (ZPR - Madrid Central)" if es_urbana else "Vía de Alta Capacidad / Autovía"
            st.info(f"📍 **Clasificación Real:** {tipo_via}")
            
            s1, s2 = st.columns(2)
            s1.write(f"🔄 **Sentido de Circulación:**\n{'Sentido Único' if info.get('oneway') == 1 else 'Doble Sentido'}")
            s2.write(f"🏢 **Uso de Suelo:**\n{'Residencial / Turístico' if es_urbana else 'Comercial / Logístico'}")
            
            s3, s4 = st.columns(2)
            s3.write(f"♿ **Accesibilidad:**\nPrioridad Peatonal" if es_urbana else "Acceso Vehicular Libre")
            s4.write(f"🏢 **Estructura Física:**\n{'Subterránea (Túnel)' if 'túnel' in nombre_calle else 'Nivel Superficie'}")

            # Alerta de Integridad de Datos
            if error_sensor:
                st.warning(f"⚠️ **Compensación IA:** El sensor reportó {int(v_sensor)} km/h. Se ha forzado el límite de 50 km/h por cumplimiento de normativa urbana.")

        with col_met:
            st.markdown("### ☁️ Factores de Entorno y Contexto")
            m1, m2 = st.columns(2)
            m1.metric("Temperatura", f"{info.get('temperature', '5.4')} °C") 
            m2.metric("Precipitación", f"{info.get('precipitation', 0.0)} mm")
            
            # Contexto Temporal Validado
            st.success(f"📅 **Contexto Operativo:** Día {contexto_validado}") 
            st.caption("Nota: El calendario se valida contra el reloj del sistema para asegurar la precisión del análisis de tráfico.")
            
else:
    st.error("🚨 Error de comunicación con la API. El sistema de predicción está fuera de línea.")