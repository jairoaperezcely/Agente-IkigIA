import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import requests
import tempfile
import os
from PIL import Image # Nueva librería para imágenes
from datetime import date

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="IkigAI V1.9 - Visión Multimodal", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

# Diccionario de Roles Completo (Se mantienen todos los previos)
ROLES = {
    "Coach de Alto Desempeño": "Productividad, ROI cognitivo y mentalidad de abundancia.",
    "Director Centro Telemedicina": "Estratega en Salud Digital e IA. Innovación y Hospital Virtual.",
    "Vicedecano Académico": "Gestión UNAL, normativa y liderazgo institucional.",
    "Director de UCI": "Rigor clínico, seguridad del paciente y datos en cuidado crítico.",
    "Consultor Salud Digital": "Estrategia BID/MinSalud. Territorio e interculturalidad.",
    "Profesor Universitario": "Pedagogía disruptiva y mentoría médica.",
    "Estratega de Trading": "Análisis técnico, gestión de riesgo y psicología de mercado."
}

# --- 2. FUNCIONES DE LECTURA (PDF, DOCX, EXCEL, WEB, YT) ---
# (Se mantienen las funciones de lectura previas...)

# --- 3. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state:
    st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None

# --- 4. BARRA LATERAL: CONECTORES DE LECTURA ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    
    st.divider()
    st.subheader(f"🔌 Fuentes para {rol_activo}")
    
    tab_files, tab_links, tab_vision = st.tabs(["📄 Archivos", "🔗 Links", "👁️ Visión"])
    
    with tab_files:
        up_files = st.file_uploader("Cargar PDF, Word, Excel:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer Documentos"):
            # (Lógica de lectura de archivos previa...)
            st.success("Documentos leídos.")

    with tab_links:
        url_w = st.text_input("URL Web:")
        url_y = st.text_input("URL YouTube:")
        if st.button("🌐 Leer Links"):
            # (Lógica de lectura de links previa...)
            st.success("Fuentes externas leídas.")

    with tab_vision:
        img_file = st.file_uploader("Subir imagen (JPG, PNG, captura):", type=['jpg', 'jpeg', 'png'])
        if img_file:
            st.session_state.temp_image = Image.open(img_file)
            st.image(st.session_state.temp_image, caption="Imagen cargada para análisis", use_container_width=True)

# --- 5. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

# Chat Multimodal
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("¿Qué analizamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Construcción del mensaje multimodal
        system_p = f"""
        IDENTIDAD: IkigAI en modo {rol_activo}. {ROLES[rol_activo]}
        CONTENIDO LEÍDO PREVIAMENTE: {st.session_state.biblioteca[rol_activo][:500000]}
        INSTRUCCIÓN: Analiza el prompt y, si hay una imagen, relacionala con el contexto de tu rol.
        Estilo directo, clínico y ejecutivo. Sin clichés.
        """
        
        inputs = [system_p, prompt]
        if st.session_state.temp_image:
            inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        
        # Limpiamos la imagen tras el análisis para la próxima consulta
        st.session_state.temp_image = None
