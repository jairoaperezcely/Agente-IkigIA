import streamlit as st
import google.generativeai as genai
from datetime import date

# --- CONFIGURACIÓN E IDENTIDADES ---
st.set_page_config(page_title="IkigAI V1.4", page_icon="🧬", layout="wide")

# Autenticación (Se recomienda usar st.secrets["GOOGLE_API_KEY"])
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

ROLES = {
    "Coach de Alto Desempeño": "Foco en ROI cognitivo, bienestar y eliminación de procastinación oculta.",
    "Director Centro Telemedicina": "Estratega en Salud Digital, IA e innovación en la Universidad Nacional.",
    "Vicedecano Académico": "Gestión administrativa, normativa académica y liderazgo institucional.",
    "Director de UCI": "Rigor clínico, seguridad del paciente y medicina basada en evidencia.",
    "Consultor Salud Digital": "Diseño de programas para el BID/MinSalud con enfoque territorial e intercultural.",
    "Profesor Universitario": "Mentoría, diseño curricular médico y pedagogía disruptiva para el territorio.",
    "Estratega de Trading": "Análisis técnico, gestión de riesgo y psicología del mercado aplicada a la toma de decisiones."
}

# --- INTERFAZ ---
with st.sidebar:
    st.title("🧬 IkigAI")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    st.divider()
    st.caption(f"Activo: {rol_activo}")

st.header(f"Panel de Control: {rol_activo}")

# Entrada de objetivos
input_text = st.text_area("Describa sus objetivos, tareas o el escenario a analizar:", height=150)

if st.button("🚀 Ejecutar Análisis IkigAI"):
    if input_text:
        with st.spinner("Procesando bajo lógica de alto desempeño..."):
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Prompt que integra los nuevos roles
            sistema = f"""
            Eres IkigAI en modo {rol_activo}.
            CONTEXTO: {ROLES[rol_activo]}
            
            INSTRUCCIONES:
            - Si es 'Profesor': Enfócate en cómo simplificar conceptos complejos y generar impacto social.
            - Si es 'Trading': Analiza el riesgo, la estructura del mercado y la disciplina emocional.
            - Detecta si hay procastinación en lo que el usuario describe.
            - Estilo: Directo, ejecutivo, sin clichés.
            """
            
            res = model.generate_content([sistema, input_text])
            st.markdown("---")
            st.subheader("💡 Respuesta Estratégica")
            st.write(res.text)
    else:
        st.warning("Por favor, ingrese información para iniciar.")
