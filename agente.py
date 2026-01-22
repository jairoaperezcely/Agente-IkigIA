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
st.set_page_config(page_title="Agente V55 (Debug)", page_icon="🔧", layout="wide")
MODELO_USADO = 'gemini-1.5-flash' # Modelo estándar y estable

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
PERFIL: Vicedecano Académico (UNAL) y Director UCI (HUN).
INSTRUCCIÓN: Tienes acceso a Google Search. ÚSALO para buscar el Salario Mínimo 2026.
SI LA BÚSQUEDA FALLA: No inventes. Di "Error de conexión".
"""

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("🔧 Diagnóstico V55")
    
    # 1. Chequeo de Librería
    try:
        ver = genai.__version__
        st.write(f"📚 Librería: `{ver}`")
        if ver < "0.8.3":
            st.error("❌ Librería Obsoleta. El servidor ignoró requirements.txt")
        else:
            st.success("✅ Librería Actualizada")
    except:
        st.error("❌ Librería no detectada")

    # 2. Chequeo de API Key
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key en Secrets")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    rol = st.selectbox("Rol:", ["Director UCI", "Vicedecano", "Socio Estratégico"])

# ==========================================
# INTERFAZ DE CHAT
# ==========================================
st.title("🤖 Agente V55: Prueba de Conexión")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Escribe: Salario Mínimo 2026"):
    if not api_key: st.error("Falta API Key"); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        genai.configure(api_key=api_key)
        
        # --- ZONA DE PRUEBA DE CONEXIÓN ---
        try:
            # 1. Definimos la herramienta explícitamente
            herramienta_search = {'google_search': {}}
            
            # 2. Instanciamos el modelo con la herramienta
            model = genai.GenerativeModel(
                model_name=MODELO_USADO,
                tools=[herramienta_search], 
                system_instruction=MEMORIA_MAESTRA
            )
            
            # 3. Prompt agresivo para forzar la búsqueda
            prompt_final = f"""
            FECHA: {date.today()}.
            PREGUNTA: {p}
            IMPORTANTE: Usa la herramienta google_search obligatoriamente para responder.
            """
            
            # 4. Generación
            st.info("🔄 Conectando con Google Search...")
            response = model.generate_content(prompt_final, stream=True)
            
            full_text = ""
            text_placeholder = st.empty()
            
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    text_placeholder.markdown(full_text + "▌")
            
            text_placeholder.markdown(full_text)
            st.session_state.messages.append({"role": "assistant", "content": full_text})
            st.success("✅ ¡Conexión Exitosa!")

        except Exception as e:
            # --- CAPTURA DE ERROR REAL ---
            st.error("💥 LA CONEXIÓN FALLÓ. MIRA EL ERROR ABAJO:")
            st.code(str(e))
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})
            
            # Guía de Solución según el error
            err_str = str(e)
            if "Unknown field" in err_str:
                st.warning("Diagnóstico: El servidor sigue usando una librería vieja incompatible con 'google_search'.")
            elif "API key not valid" in err_str or "403" in err_str:
                st.warning("Diagnóstico: La API Key es incorrecta o no tiene permisos.")
            elif "404" in err_str:
                st.warning("Diagnóstico: El modelo 'gemini-1.5-flash' no está disponible para tu API Key.")
            elif "GoogleSearchRetrieval" in err_str:
                st.warning("Diagnóstico: Conflicto de nombres en la librería.")
