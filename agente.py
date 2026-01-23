import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os
from io import BytesIO
import json
from datetime import date

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente de Alto Desempeño V10", page_icon="🚀", layout="wide")

# --- AUTENTICACIÓN AUTOMÁTICA ---
# Busca la clave en los secretos de Streamlit (Local: .streamlit/secrets.toml | Web: Dashboard de Streamlit)
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
else:
    st.error("❌ No se encontró la API Key. Configúrala en st.secrets como 'GOOGLE_API_KEY'.")
    st.stop()

# --- FUNCIONES DE LECTURA DE TEXTO (PDF/DOCX) ---
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages])

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- LÓGICA DE MEMORIA Y ESTADO ---
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""

# --- BARRA LATERAL (CONTROLES ESTRATÉGICOS) ---
with st.sidebar:
    st.header("🎯 Coach Strategy Panel")
    
    # Selección de Rol con el nuevo perfil integrado
    rol = st.selectbox("Cambiar Enfoque del Agente:", [
        "Coach de Alto Desempeño",
        "Vicedecano Académico", 
        "Experto en Telesalud",
        "Mentor de Trading"
    ])
    
    prompts_roles = {
        "Coach de Alto Desempeño": """Eres un Coach de Élite multidisciplinario. 
        Tu misión: Maximizar la productividad y sostenibilidad del usuario (Médico/Consultor).
        - Detecta procrastinación y sesgos en cada entrada.
        - Desafía creencias limitantes sobre el dinero y el éxito profesional.""",
        "Vicedecano Académico": "Eres un directivo riguroso de la Universidad Nacional. Basado en normas.",
        "Experto en Telesalud": "Experto en Salud Digital y normativa colombiana (Ley 1419/Res 2654).",
        "Mentor de Trading": "Trader Institucional. Enfoque en Smart Money y gestión de riesgo en Commodities."
    }

    st.divider()
    temp_val = st.slider("Precisión vs Creatividad:", 0.0, 1.0, 0.3)
    
    # Gestión de Archivos
    uploaded_docs = st.file_uploader("Subir Contexto (PDF/Word)", type=['pdf', 'docx'], accept_multiple_files=True)
    if uploaded_docs and st.button("🧠 Alimentar Memoria"):
        texto_acumulado = ""
        for doc in uploaded_docs:
            if doc.type == "application/pdf": texto_acumulado += get_pdf_text(doc)
            else: texto_acumulado += get_docx_text(doc)
        st.session_state.contexto_texto = texto_acumulado
        st.success("Contexto actualizado.")

# --- INTERFAZ DE CHAT ---
st.title(f"⚡ {rol}")

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("Escribe tu reporte o consulta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel('gemini-1.5-pro', generation_config={"temperature": temp_val})
            
            # Prompt Maestro Inyectado
            master_prompt = f"""
            IDENTIDAD: {prompts_roles[rol]}
            REGLAS: Sé directo, profesional, evita clichés robóticos. Usa APA 7 para citar si hay documentos.
            
            CONTEXTO DE ARCHIVOS: {st.session_state.contexto_texto[:500000]}
            
            ESTRUCTURA DE RESPUESTA SI ERES COACH:
            1. Diagnóstico de Prioridades/Procrastinación.
            2. Ejercicio de Pensamiento Crítico o Creativo.
            3. Desafío de Creencia Financiera (si aplica).
            
            SOLICITUD: {prompt}
            """
            
            response = model.generate_content(master_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Error en generación: {e}")
