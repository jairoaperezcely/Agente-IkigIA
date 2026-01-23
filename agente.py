import streamlit as st
import google.generativeai as genai
from datetime import date

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="IkigAI: Sistema Operativo de Liderazgo", page_icon="🧬", layout="wide")

# --- AUTENTICACIÓN AUTOMÁTICA ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("⚠️ Falta la configuración de 'GOOGLE_API_KEY' en los secretos.")
    st.stop()

# --- DICCIONARIO DE ROLES (PROMPTS DE IDENTIDAD) ---
ROLES = {
    "Coach de Alto Desempeño": {
        "icono": "🚀",
        "prompt": "Eres el Coach de Alto Desempeño de IkigAI. Tu foco es la productividad estratégica, el bienestar del líder y romper patrones de procrastinación. Desafía creencias limitantes sobre éxito y dinero."
    },
    "Director Centro Telemedicina": {
        "icono": "🌐",
        "prompt": "Eres el CSO (Chief Strategy Officer) de IkigAI para el Centro de Telemedicina e IA de la UNAL. Tu foco es la innovación, la IA aplicada y la escalabilidad de proyectos tecnológicos con impacto social."
    },
    "Vicedecano Académico": {
        "icono": "🏛️",
        "prompt": "Eres el Arquitecto Normativo de IkigAI. Experto en la Universidad Nacional. Redactas resoluciones, actas y gestionas la burocracia académica de forma eficiente y diplomática."
    },
    "Director de UCI": {
        "icono": "🏥",
        "prompt": "Eres el Consultor Clínico de IkigAI. Foco en Medicina Basada en Evidencia, seguridad del paciente en el HUN y uso de datos para decisiones críticas en cuidado intensivo."
    },
    "Consultor BID/MinSalud": {
        "icono": "🌍",
        "prompt": "Eres el Arquitecto de Políticas Públicas de IkigAI. Especialista en Telesalud, interculturalidad y diseño de programas para territorios (PDET/ZOMAC)."
    }
}

# --- ESTADO DE LA SESIÓN ---
if "messages" not in st.session_state: st.session_state.messages = []

# --- BARRA LATERAL: EL SELECTOR DE IDENTIDAD ---
with st.sidebar:
    st.title("🧬 IkigAI")
    st.caption("Sistema de Gestión Estratégica Integral")
    st.divider()
    
    # Cambio de rol dinámico
    rol_seleccionado = st.selectbox("Seleccione el Rol Activo:", list(ROLES.keys()))
