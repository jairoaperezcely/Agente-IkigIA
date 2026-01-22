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
from google.api_core.exceptions import InvalidArgument

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agente V53 (Políglota)", page_icon="🧬", layout="wide")
MODELO_USADO = 'gemini-2.5-flash'

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
# FUNCIONES AUXILIARES (SIMPLIFICADAS PARA V53)
# ==========================================
# ... (Mantenemos la lógica de documentos pero simplificada para asegurar conexión) ...
def create_docx(text):
    doc = docx.Document()
    doc.add_paragraph(text)
    b = BytesIO(); doc.save(b); b.seek(0); return b

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # VERIFICACIÓN DE VERSIÓN
    ver = genai.__version__
    st.caption(f"Librería Instalada: v{ver}")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Login Automático")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    usar_google = st.toggle("🌐 Búsqueda Google", value=True)
    rol = st.selectbox("Rol:", ["Socio Estratégico", "Vicedecano", "Director UCI"])
    
    if st.button("🗑️ Limpiar Chat"): st.session_state.messages = []; st.rerun()

# ==========================================
# LÓGICA DE CONEXIÓN "POLÍGLOTA" (LA SOLUCIÓN)
# ==========================================
def generar_respuesta(prompt, historial):
    # Configurar API
    genai.configure(api_key=api_key)
    
    # Preparar el contexto
    full_prompt = f"FECHA HOY: {date.today()}. HISTORIAL: {historial}. CONSULTA: {prompt}"
    
    # ---------------------------------------------------------
    # INTENTO 1: MÉTODO MODERNO (google_search)
    # ---------------------------------------------------------
    if usar_google:
        try:
            print("Intento 1: Moderno...")
            tools = [{'google_search': {}}]
            model = genai.GenerativeModel(MODELO_USADO, tools=tools, system_instruction=MEMORIA_MAESTRA)
            return model.generate_content(full_prompt, stream=True)
        except Exception as e:
            error_msg = str(e)
            # Si el servidor rechaza el moderno, probamos el antiguo
            if "Unknown field" in error_msg or "400" in error_msg:
                pass # Vamos al Intento 2
            else:
                return f"Error Técnico: {e}"

    # ---------------------------------------------------------
    # INTENTO 2: MÉTODO CLÁSICO (google_search_retrieval)
    # ---------------------------------------------------------
    if usar_google:
        try:
            print("Intento 2: Clásico...")
            # Esta es la llave vieja que el servidor sí podría tener
            tools = [{'google_search_retrieval': {}}]
            model = genai.GenerativeModel(MODELO_USADO, tools=tools, system_instruction=MEMORIA_MAESTRA)
            return model.generate_content(full_prompt, stream=True)
        except Exception as e:
            # Si ambos fallan, vamos sin herramientas
            print(f"Fallo Clásico: {e}")

    # ---------------------------------------------------------
    # INTENTO 3: SIN HERRAMIENTAS (Memoria Pura)
    # ---------------------------------------------------------
    print("Intento 3: Memoria...")
    model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
    return model.generate_content(full_prompt + " (NOTA: No pude buscar en internet, responde con lo que sepas).", stream=True)

# ==========================================
# INTERFAZ DE CHAT
# ==========================================
st.title(f"🤖 Agente V53: {rol}")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Escribe tu instrucción..."):
    if not api_key: st.warning("Falta API Key"); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        hist_str = str(st.session_state.messages[-5:])
        
        # Llamamos a la función políglota
        try:
            response_stream = generar_respuesta(p, hist_str)
            
            if isinstance(response_stream, str):
                st.error(response_stream) # Fue un error grave
            else:
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
