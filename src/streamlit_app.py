import streamlit as st  # type: ignore

st.set_page_config(
    page_title="SmartTrafficFlow",
    page_icon="🚘",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 0rem;
            z-index:1
        }

        header {
            z-index: 0 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

"""
### 🚘 SmartTrafficFlow

Predicción inteligente de tráfico

---

#### Visualización
Resumen del tráfico en tiempo real
"""
