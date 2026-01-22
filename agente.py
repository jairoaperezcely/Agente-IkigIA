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
# CONFIGURACIÓN Y DIAGNÓSTICO
# ==========================================
st.set_page_config(page_title="Agente V52 (Diagnóstico)", page_icon="🕵️", layout="wide")
MODELO_USADO = 'gemini-2.5-flash'

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
Eres un Líder Transformador en Salud (Vicedecano, Intensivista, Innovador).
Responde con visión estratégica, humanista y basada en evidencia.
Si te preguntan datos actuales (2026), DEBES usar Google Search.
"""

# ==========================================
# BARRA LATERAL (LA VERDAD TÉCNICA)
# ==========================================
with st.sidebar:
    st.header("🕵️ Diagnóstico Forense")
    
    # 1. VERSIÓN REAL INSTALADA
    ver = genai.__version__
    
    if ver >= "0.8.3":
        st.success(f"✅ Librería: v{ver} (Correcta)")
        estado_red = "ONLINE"
    else:
        st.error(f"❌ Librería: v{ver} (OBSOLETA)")
        st.warning("El servidor sigue usando caché vieja. Modifica requirements.txt agregando 'simplejson' para forzarlo.")
        estado_red = "OFFLINE"

    # 2. API KEY
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key Detectada")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    st.divider()
    usar_search = st.toggle("🌐 Búsqueda Google", value=(estado_red == "ONLINE"))
    st.info("Si activas esto y sale error, lee el mensaje rojo.")

# ==========================================
# LÓGICA DE RESPUESTA SIMPLIFICADA (PARA TEST)
# ==========================================
st.title("🤖 Agente V52: Test de Conexión")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Pregunta por el salario mínimo 2026..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        if not api_key: st.error("Falta API Key"); st.stop()
        
        genai.configure(api_key=api_key)
        
        # --- INTENTO DE CONEXIÓN CRUDA ---
        try:
            tools = []
            if usar_search:
                # Intentamos invocar la herramienta moderna
                tools = [{'google_search': {}}]
            
            model = genai.GenerativeModel(MODELO_USADO, tools=tools, system_instruction=MEMORIA_MAESTRA)
            
            # Prompt con fecha para forzar búsqueda
            full_prompt = f"FECHA HOY: {date.today()}. Consulta: {p}"
            
            response = model.generate_content(full_prompt, stream=True)
            
            def stream():
                for chunk in response: yield chunk.text
            
            st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": "Respuesta generada."})
            
        except Exception as e:
            # AQUÍ VEREMOS EL ERROR REAL
            st.error(f"💥 ERROR CRÍTICO: {e}")
            st.markdown("---")
            st.markdown("**Interpretación del Error:**")
            err_str = str(e)
            if "Unknown field" in err_str:
                st.write("👉 **Culpable:** El servidor. Sigue con la librería vieja v0.5.x o v0.7.x.")
            elif "403" in err_str or "API key not valid" in err_str:
                st.write("👉 **Culpable:** La API Key. No tiene permisos o es inválida.")
            elif "400" in err_str and "google_search" in err_str:
                 st.write("👉 **Culpable:** Conflicto de versiones. Requiere 'Hard Reset'.")
            else:
                st.write("👉 Error desconocido. Copia esto y envíaselo a tu ingeniero.")
