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
import re 
import pandas as pd
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor as PtxRGB
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agente V54 (Fixed)", page_icon="🧬", layout="wide")

# --- CORRECCIÓN CRÍTICA: MODELO VÁLIDO ---
MODELO_USADO = 'gemini-1.5-flash' 
# =========================================

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
PERFIL DEL USUARIO (QUIÉN SOY):
- Soy un Líder Transformador en Salud: Médico Especialista en Anestesiología y Cuidado Crítico (UCI), Epidemiólogo Clínico y Doctorando en Bioética.
- Roles de Alto Impacto: Vicedecano Académico (UNAL), Coordinador Telemedicina, Director UCI (HUN).

INSTRUCCIONES:
1. TONO: Estratégico, Empático y Visionario.
2. FECHA ACTUAL: Estás en 2026. Si preguntan datos actuales (Salario, Dólar, Decretos), DEBES BUSCAR EN GOOGLE.
3. FORMATO: Estructurado, con tablas y citas si es necesario.
"""

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def create_docx(text):
    doc = docx.Document()
    doc.add_paragraph(text)
    b = BytesIO(); doc.save(b); b.seek(0); return b

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración V54")
    
    # VERIFICACIÓN DE VERSIÓN
    ver = genai.__version__
    st.caption(f"Librería: v{ver}")
    st.caption(f"Modelo: {MODELO_USADO}")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Login Automático")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    usar_google = st.toggle("🌐 Búsqueda Google", value=True)
    rol = st.selectbox("Rol:", ["Socio Estratégico", "Vicedecano", "Director UCI"])
    
    if st.button("🗑️ Limpiar Chat"): st.session_state.messages = []; st.rerun()

# ==========================================
# LÓGICA DE CONEXIÓN
# ==========================================
def generar_respuesta(prompt, historial):
    genai.configure(api_key=api_key)
    full_prompt = f"FECHA HOY: {date.today()}. HISTORIAL: {historial}. CONSULTA: {prompt}"
    
    # INTENTO PRINCIPAL
    if usar_google:
        try:
            # Usamos la herramienta moderna con el modelo CORRECTO
            tools = [{'google_search': {}}]
            model = genai.GenerativeModel(MODELO_USADO, tools=tools, system_instruction=MEMORIA_MAESTRA)
            return model.generate_content(full_prompt, stream=True)
        except Exception as e:
            # Si falla, imprimimos el error en consola pero intentamos sin herramientas
            print(f"Error Search: {e}")
            pass # Continuar al fallback

    # FALLBACK (MEMORIA)
    model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
    return model.generate_content(full_prompt + " (NOTA: No se pudo conectar a Google, usa tu conocimiento base).", stream=True)

# ==========================================
# INTERFAZ DE CHAT
# ==========================================
st.title(f"🤖 Agente V54: {rol}")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Consulta sobre el salario 2026..."):
    if not api_key: st.warning("Falta API Key"); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        hist_str = str(st.session_state.messages[-5:])
        try:
            response_stream = generar_respuesta(p, hist_str)
            text_placeholder = st.empty()
            full_text = ""
            for chunk in response_stream:
                if chunk.text:
                    full_text += chunk.text
                    text_placeholder.markdown(full_text + "▌")
            text_placeholder.markdown(full_text)
            st.session_state.messages.append({"role": "assistant", "content": full_text})
                
        except Exception as e:
            st.error(f"Error inesperado: {e}")
