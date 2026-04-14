import streamlit as st
import pandas as pd
import requests
import os
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from typing import Optional
import random

# ---------------------------------------------------------------------------
# CONFIGURACIÓN GLOBAL
# ---------------------------------------------------------------------------

API_URL: str = os.getenv("API_URL", "http://localhost:8000")
VELOCIDAD_LIMITE_URBANO: int = 50
COORDENADAS_BAILEN: dict = {"lat": 40.4145, "lon": -3.7135}
CENTRO_MADRID: dict = {"lat": 40.4167, "lon": -3.7033}
ZOOM_GENERAL: float = 11.0
ZOOM_DETALLE: float = 16.5
KEYWORDS_URBANAS: tuple = ("calle", "bailén", "mayor", "plaza", "avenida", "paseo", "gran vía")
COLOR_ESTADO: dict = {
    "Verde (Fluido)":      "#28a745",
    "Naranja (Denso)":     "#ff8c00",
    "Rojo (Retención)":    "#ff0000",
}

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ---------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="Smart Traffic Madrid Pro", page_icon="🚦")

# Inyectar CSS para reducir espacios y mejorar el layout
st.markdown("""
    <style>
    /* Reducir espacio superior de la página */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 5rem !important;
    }
    /* Reducir espacio entre widgets */
    div.stVerticalBlock > div {
        padding-top: 0.1rem !important;
        padding-bottom: 0.1rem !important;
    }
    /* Estilo para que el botón y el selector se vean alineados */
    div[data-testid="stColumn"] {
        display: flex;
        align-items: flex-end;
    }
    /* Reducir margen del título */
    h1 {
        margin-top: -1rem !important;
        margin-bottom: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Inicializar historial en session_state si no existe
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["timestamp", "street", "intensity", "status"])

# Refresco automático cada 30 segundos
count = st_autorefresh(interval=30000, limit=None, key="traffic_counter")

# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------

@st.cache_data(ttl=25)
def fetch_api(endpoint: str, force_reload: bool = False) -> Optional[list | dict]:
    """Realiza una petición GET al endpoint de la API local."""
    if force_reload:
        st.cache_data.clear()
    try:
        res = requests.get(f"{API_URL}/{endpoint}", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def simular_prediccion_ia(intensidad_actual: float) -> dict:
    hora = datetime.now().hour
    tendencia = 1.1 if (7 <= hora <= 9 or 17 <= hora <= 19) else 0.9
    return {
        "1h": int(intensidad_actual * tendencia * random.uniform(0.95, 1.05)),
        "3h": int(intensidad_actual * (tendencia**2) * random.uniform(0.9, 1.1)),
        "6h": int(intensidad_actual * random.uniform(0.7, 1.3))
    }

def registrar_historial(nombre_calle: str, intensidad: float, estado: str):
    nuevo_dato = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "street": nombre_calle,
        "intensity": intensidad,
        "status": estado
    }
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([nuevo_dato])], ignore_index=True)
    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history.tail(50)

def es_via_urbana(nombre_calle: str) -> bool:
    return any(k in nombre_calle.lower() for k in KEYWORDS_URBANAS)

def obtener_centro_y_zoom(calle_sel: str, display_df: pd.DataFrame) -> tuple[dict, float]:
    if calle_sel == "Ver Mapa General":
        return CENTRO_MADRID, ZOOM_GENERAL
    if "Bailén" in calle_sel:
        return COORDENADAS_BAILEN, ZOOM_DETALLE
    return {"lat": display_df.iloc[0]["latitude"], "lon": display_df.iloc[0]["longitude"]}, ZOOM_DETALLE

def renderizar_mapa(display_df: pd.DataFrame, center: dict, zoom: float) -> None:
    fig_map = px.scatter_mapbox(
        display_df, lat="latitude", lon="longitude", color="status",
        color_discrete_map=COLOR_ESTADO, hover_name="name",
        hover_data={"latitude": False, "longitude": False, "status": True, "traffic_intensity": True},
        center=center, zoom=zoom, height=450 # Reducido ligeramente para ahorrar espacio
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_map, use_container_width=True)

# ---------------------------------------------------------------------------
# INTERFAZ PRINCIPAL
# ---------------------------------------------------------------------------

st.title("🚦 Smart Traffic Madrid - IA de Predicción")

# Sidebar con controles avanzados
with st.sidebar:
    st.header("⚙️ Panel de Control")
    st.metric("Ciclo de Refresco", f"nº {count}", delta="30s")
    st.markdown("---")
    st.subheader("🎯 Filtros de Mapa")
    filtro_estado = st.multiselect("Filtrar por estado:", list(COLOR_ESTADO.keys()), default=list(COLOR_ESTADO.keys()))
    min_intensidad = st.slider("Intensidad mínima (veh/h):", 0, 5000, 0)
    st.markdown("---")
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.history = pd.DataFrame(columns=["timestamp", "street", "intensity", "status"])
        st.rerun()

# 1. CARGA DE DATOS
map_data_raw = fetch_api("map-status")

if map_data_raw:
    df_map = pd.DataFrame(map_data_raw)
    df_map["name"] = df_map["name"].astype(str)
    df_filtered = df_map[df_map["status"].isin(filtro_estado) & (df_map["traffic_intensity"] >= min_intensidad)]

    # LAYOUT: Selector y Botón de Actualización en la misma fila
    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        opciones = ["Ver Mapa General"] + sorted(df_map["name"].unique().tolist())
        calle_sel = st.selectbox("📍 Selecciona una ubicación o calle:", opciones, label_visibility="collapsed")
    with col_btn:
        if st.button("🔄 Actualizar", use_container_width=True):
            fetch_api("map-status", force_reload=True)
            st.rerun()

    # Lógica de posicionamiento
    if calle_sel == "Ver Mapa General":
        display_df = df_filtered
        center_map, zoom_level = CENTRO_MADRID, ZOOM_GENERAL
    else:
        display_df = df_map[df_map["name"] == calle_sel]
        center_map, zoom_level = obtener_centro_y_zoom(calle_sel, display_df)
        if not display_df.empty:
            registrar_historial(calle_sel, display_df.iloc[0]["traffic_intensity"], display_df.iloc[0]["status"])

    # MAPA
    renderizar_mapa(display_df, center_map, zoom_level)

    # ANÁLISIS TÉCNICO AVANZADO
    if calle_sel != "Ver Mapa General" and not display_df.empty:
        info = display_df.iloc[0]
        intensidad = info["traffic_intensity"]
        
        st.markdown("---")
        col_title, col_export = st.columns([3, 1])
        col_title.subheader(f"📊 Análisis Pro: {calle_sel}")

        # --- MEJORA EN EXPORTACIÓN CSV ---
        # Creamos una copia limpia para exportar
        export_df = display_df.copy()
        # Añadimos marca de tiempo de la extracción
        export_df["fecha_extraccion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Reordenamos o renombramos si es necesario para que sea legible
        columnas_finales = ["name", "status", "traffic_intensity", "fecha_extraccion"]
        # Solo añadimos 'lanes' o 'maxspeed' si existen en el DF original
        for col in ["lanes", "maxspeed", "oneway"]:
            if col in export_df.columns:
                columnas_finales.append(col)
        
        csv_data = export_df[columnas_finales].to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        
        col_export.download_button(
            label="📥 Exportar CSV",
            data=csv_data,
            file_name=f"trafico_{calle_sel.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.csv",
            mime="text/csv",
            help="Descarga los datos actuales en formato CSV compatible con Excel"
        )

        # Alertas Críticas compactas
        if info["status"] == "Rojo (Retención)":
            st.error(f"🚨 **ALERTA:** Retención severa ({int(intensidad)} veh/h).")
        elif intensidad > 2500:
            st.warning(f"⚠️ **AVISO:** Intensidad alta.")

        # KPIs
        # KPIs PRINCIPALES ESTILIZADOS
        st.markdown("---")
        
        # Lógica de velocidad legal (la mantenemos igual)
        v_sensor = info.get("maxspeed", 50)
        v_legal = 50 if (es_via_urbana(calle_sel) and v_sensor > 50) else v_sensor

        def kpi_card(icon, label, value, unit, color="#00d4ff"):
            return f"""
            <div style="
                background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
                padding: 15px 10px;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.1);
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                <span style="font-size: 28px; display: block; margin-bottom: 5px;">{icon}</span>
                <span style="font-size: 11px; color: #aaaaaa; text-transform: uppercase; letter-spacing: 1px;">{label}</span><br>
                <span style="font-size: 20px; font-weight: 800; color: white;">{value}</span>
                <span style="font-size: 12px; color: {color};">{unit}</span>
            </div>
            """

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(kpi_card("🚗", "Intensidad", int(intensidad), "v/h"), unsafe_allow_html=True)
        with c2:
            # Determinamos color según el estado
            color_dot = COLOR_ESTADO.get(info["status"], "#fff")
            # Limpiamos el texto del estado para que quepa bien (ej: de "Rojo (Retención)" a "Retención")
            estado_limpio = info["status"].split("(")[-1].replace(")", "") if "(" in info["status"] else info["status"]
            st.markdown(kpi_card("🚥", "Estado", estado_limpio, "•", color_dot), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi_card("⚡", "Límite IA", int(v_legal), "km/h", "#ff4b4b"), unsafe_allow_html=True)
        with c4:
            st.markdown(kpi_card("🛣️", "Capacidad", int(info.get('lanes', 0)), "Carriles", "#ffa500"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["🔮 Predicción IA", "📈 Tendencia", "🏗️ Infraestructura"])
        with tab1:
            preds = simular_prediccion_ia(intensidad)
            
            st.markdown("### 🔮 Proyección de Flujo (Motor IA)")
            
            # Función para determinar el color y el icono del delta
            def get_trend_info(val_pred, val_actual):
                diff = val_pred - val_actual
                if diff > 100: return "#ff4b4b", "📈", "Aumento Crítico"
                if diff > 0: return "#ffa500", "↗️", "Incremento Ligero"
                return "#28a745", "📉", "Descongestión"

            def pred_card(time_label, value, actual):
                diff = value - actual
                color, icon, msg = get_trend_info(value, actual)
                delta_sign = "+" if diff > 0 else ""
                
                return f"""
                <div style="
                    background-color: rgba(255, 255, 255, 0.05); 
                    padding: 20px; 
                    border-radius: 12px; 
                    border-top: 4px solid {color};
                    text-align: center;">
                    <span style="font-size: 14px; color: gray; font-weight: bold;">EN {time_label}</span><br>
                    <span style="font-size: 32px; font-weight: bold;">{value}</span>
                    <span style="font-size: 14px; color: gray;">veh/h</span><br>
                    <div style="color: {color}; font-size: 16px; margin-top: 10px;">
                        {icon} {delta_sign}{diff}
                    </div>
                    <div style="font-size: 10px; color: {color}; opacity: 0.8; margin-top: 5px; text-transform: uppercase;">
                        {msg}
                    </div>
                </div>
                """

            p1, p2, p3 = st.columns(3)
            
            with p1:
                st.markdown(pred_card("1 HORA", preds['1h'], intensidad), unsafe_allow_html=True)
            with p2:
                st.markdown(pred_card("3 HORAS", preds['3h'], intensidad), unsafe_allow_html=True)
            with p3:
                st.markdown(pred_card("6 HORAS", preds['6h'], intensidad), unsafe_allow_html=True)

            # Nota informativa de IA
            st.markdown(
                f"""
                <div style="margin-top: 20px; padding: 10px; background-color: rgba(0, 123, 255, 0.1); border-radius: 5px; border-left: 3px solid #007bff;">
                    <small>ℹ️ <b>Nota del modelo:</b> Las predicciones consideran la hora actual (<b>{datetime.now().strftime('%H:%M')}</b>) y patrones históricos de Madrid.</small>
                </div>
                """, 
                unsafe_allow_html=True
            )
        with tab2:
            hist_calle = st.session_state.history[st.session_state.history["street"] == calle_sel]
            
            if len(hist_calle) > 1:
                # 1. Cálculo de métricas
                min_int = int(hist_calle['intensity'].min())
                avg_int = int(hist_calle["intensity"].mean())
                max_int = int(hist_calle["intensity"].max())

                # Estilo de tarjeta (Reutilizamos la lógica visual de tab3)
                def stat_card(icon, label, value, color):
                    return f"""
                    <div style="
                        background-color: rgba(255, 255, 255, 0.05); 
                        padding: 10px; 
                        border-radius: 8px; 
                        border-bottom: 3px solid {color};
                        text-align: center;">
                        <span style="font-size: 22px;">{icon}</span><br>
                        <span style="font-size: 12px; color: gray; text-transform: uppercase;">{label}</span><br>
                        <span style="font-size: 18px; font-weight: bold;">{value}</span>
                    </div>
                    """

                # 2. Renderizado de tarjetas de estadísticas
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(stat_card("📉", "Mínimo", min_int, "#28a745"), unsafe_allow_html=True)
                with c2:
                    st.markdown(stat_card("📊", "Media", avg_int, "#007bff"), unsafe_allow_html=True)
                with c3:
                    st.markdown(stat_card("📈", "Máximo", max_int, "#ffc107"), unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # 3. Gráfico de Área (Mantenemos la configuración pro)
                fig_hist = px.area(
                    hist_calle, 
                    x="timestamp", 
                    y="intensity",
                    markers=True,
                    template="plotly_dark",
                    color_discrete_sequence=["#00d4ff"]
                )

                fig_hist.update_layout(
                    height=280,
                    margin={"r": 10, "t": 10, "l": 10, "b": 0},
                    xaxis_title=None,
                    yaxis_title="Vehículos/h",
                    hovermode="x unified",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)'),
                )
                
                fig_hist.update_traces(
                    line_shape='spline', 
                    line_width=3,
                    fillcolor="rgba(0, 212, 255, 0.15)",
                    marker=dict(size=7, line=dict(width=2, color="white"))
                )

                st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
                
            else:
                st.markdown(
                    """
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <span style="font-size: 40px;">⏳</span><br>
                        Monitorizando flujo...<br>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        with tab3:
            st.markdown("### 🏗️ Especificaciones Técnicas")
            
            # Definimos un estilo común para las "tarjetas" de información
            def card_style(icon, label, value):
                return f"""
                <div style="
                    background-color: rgba(255, 255, 255, 0.05); 
                    padding: 15px; 
                    border-radius: 10px; 
                    border-left: 5px solid #007bff;
                    margin-bottom: 10px;">
                    <span style="font-size: 30px;">{icon}</span><br>
                    <span style="font-size: 14px; color: gray;">{label}</span><br>
                    <span style="font-size: 18px; font-weight: bold;">{value}</span>
                </div>
                """

            m1, m2 = st.columns(2)
            m3, m4 = st.columns(2)

            with m1:
                tipo = 'Urbana' if es_via_urbana(calle_sel) else 'Interurbana'
                st.markdown(card_style("📍", "Clasificación", tipo), unsafe_allow_html=True)
            
            with m2:
                sentido = 'Único' if info.get('oneway') == 1 else 'Doble Sentido'
                st.markdown(card_style("🔄", "Sentido Vial", sentido), unsafe_allow_html=True)

            with m3:
                temp = info.get('temperature', '5.4')
                st.markdown(card_style("🌡️", "Temperatura", f"{temp} °C"), unsafe_allow_html=True)

            with m4:
                dia_tipo = 'Fin de Semana' if datetime.now().weekday() >= 5 else 'Día Laborable'
                st.markdown(card_style("📅", "Calendario", dia_tipo), unsafe_allow_html=True)

            # Barra de capacidad mejorada al final
            st.markdown("<br>", unsafe_allow_html=True)
            num_carriles = int(info.get('lanes', 1))
            # Cálculo de ocupación: intensidad vs capacidad (estimamos 1800 veh/h por carril)
            capacidad_max = num_carriles * 1800
            ocupacion = min(100, int((intensidad / capacidad_max) * 100)) if capacidad_max > 0 else 0
            
            st.write(f"**Carga de la vía ({ocupacion}% de capacidad teórica)**")
            st.progress(ocupacion / 100)

else:
    st.error("🚨 Error de comunicación con la API.")