import streamlit as st
import subprocess
import sys
import time
import os

# ==========================================
# 🚑 ZONA DE AUTO-CURACIÓN (INYECCIÓN)
# ==========================================
# Esto se ejecuta ANTES de cargar nada más.
try:
    import google.generativeai as genai
    versión_actual = genai.__version__
    
    # Si la versión es menor a la necesaria para Google Search
    if versión_actual < "0.8.3":
        print(f"⚠️ Versión vieja detectada ({versión_actual}). Actualizando a la fuerza...")
        st.warning(f"Actualizando sistema (v{versión_actual} -> v0.8.3)... Espere 10 segundos.")
        
        # Comando de terminal ejecutado desde Python
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai==0.8.3"])
        
        st.success("✅ Actualización completada. Reiniciando neuronas...")
        time.sleep(2)
        st.rerun() # Reinicia la app con la nueva librería
        
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai==0.8.3"])
    st.rerun()

# ==========================================
# INICIO DEL PROGRAMA NORMAL
# ==========================================
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from io import BytesIO
from datetime import date
import json

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agente V56 (Auto-Fix)", page_icon="💉", layout="wide")
MODELO_USADO = 'gemini-2.5-flash' # Modelo rápido y compatible

# ==========================================
# BARRA LATERAL (MONITOR)
# ==========================================
with st.sidebar:
    st.header("💉 Monitor V56")
    
    # Verificación final
    try:
        import google.generativeai as genai
        ver = genai.__version__
        if ver >= "0.8.3":
            st.success(f"✅ Librería: v{ver} (LISTO)")
            estado = "OK"
        else:
            st.error(f"❌ Librería: v{ver} (ERROR)")
            estado = "ERROR"
    except:
        st.error("Cargando...")
        estado = "ERROR"

    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

# ==========================================
# CEREBRO: CONEXIÓN ROBUSTA (HÍBRIDA)
# ==========================================
def conectar_cerebro(prompt):
    genai.configure(api_key=api_key)
    
    configuracion = genai.types.GenerationConfig(
        temperature=0.2
    )
    
    # ESTRATEGIA: INTENTO ESCALONADO
    # 1. Intentamos la sintaxis moderna (0.8.3)
    try:
        tools = [{'google_search': {}}]
        model = genai.GenerativeModel(MODELO_USADO, tools=tools)
        print("Intentando modo moderno...")
        return model.generate_content(prompt, stream=True)
    except Exception as e:
        print(f"Fallo moderno: {e}")
        
        # 2. Si falla, intentamos la sintaxis clásica (fallback)
        try:
            tools = [{'google_search_retrieval': {}}]
            model = genai.GenerativeModel(MODELO_USADO, tools=tools)
            print("Intentando modo clásico...")
            return model.generate_content(prompt, stream=True)
        except Exception as e2:
            # 3. Si todo falla, vamos sin herramientas (Memoria)
            print(f"Fallo clásico: {e2}")
            model = genai.GenerativeModel(MODELO_USADO)
            return model.generate_content(prompt + " (NOTA: Búsqueda falló, responde con lo que sepas).", stream=True)

# ==========================================
# INTERFAZ
# ==========================================
st.title("🤖 Agente V56: Auto-Actualizable")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Pregunta: Salario Mínimo 2026"):
    if not api_key: st.warning("Falta API Key"); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        with st.spinner("Conectando y verificando versiones..."):
            try:
                prompt_full = f"FECHA HOY: {date.today()}. Consulta: {p}. (Si necesitas datos actuales, USA GOOGLE SEARCH)."
                stream_res = conectar_cerebro(prompt_full)
                
                full_text = ""
                placeholder = st.empty()
                for chunk in stream_res:
                    if chunk.text:
                        full_text += chunk.text
                        placeholder.markdown(full_text + "▌")
                placeholder.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
                
            except Exception as e:
                st.error(f"Error Final: {e}")

