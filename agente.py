import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx # Requiere: pip install python-docx
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
from datetime import date

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.13 - Generador Ejecutivo", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y sostenibilidad del líder.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión y normativa Facultad de Medicina UNAL.",
    "Director de UCI": "Rigor clínico y datos en el HUN.",
    "Investigador Científico": "Metodología y redacción científica de alto impacto.",
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Profesor Universitario": "Pedagogía y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado."
}

# --- 2. FUNCIONES DE ESCRITURA EJECUTIVA (Nuevo) ---

def create_word_doc(title, content):
    doc = docx.Document()
    # Estilo elegante: Título centrado y tipografía limpia
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Fecha de generación: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Rol emisor: IkigAI - {st.session_state.rol_actual}")
    doc.add_divider()
    
    # El contenido se procesa por párrafos
    for p in content.split('\n'):
        if p.strip():
            doc.add_paragraph(p)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. LÓGICA DE MEMORIA Y ESTADO ---
if "biblioteca" not in st.session_state:
    st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_response" not in st.session_state: st.session_state.last_response = ""

# --- 4. BARRA LATERAL: CONECTORES DE LECTURA ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    
    st.divider()
    st.subheader(f"🔌 Fuentes para {rol_activo}")
    
    tab_files, tab_links, tab_images = st.tabs(["📄 Archivos", "🔗 Links", "🖼️ Imágenes"])
    
    # (Lógica de lectura de archivos, links e imágenes de V1.12...)

    st.divider()
    st.subheader("💾 Exportar Último Análisis")
    if st.session_state.last_response:
        btn_word = st.download_button(
            label="📄 Descargar en Word",
            data=create_word_doc(f"Informe Estratégico - {rol_activo}", st.session_state.last_response),
            file_name=f"IkigAI_{rol_activo}_{date.today()}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        st.caption("Genere un análisis para habilitar la descarga.")

# --- 5. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

# Módulo de ROI Cognitivo con salida estructurada
with st.expander("🚀 Análisis de Prioridades (ROI)"):
    tareas = st.text_area("Objetivos de hoy:", placeholder="Escriba sus tareas para priorizar...")

# Chat Multimodal e Integral
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("¿Qué entregable construimos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        system_p = f"""
        IDENTIDAD: IkigAI en modo {rol_activo}. {ROLES[rol_activo]}
        CONTENIDO LEÍDO: {st.session_state.biblioteca[rol_activo][:500000]}
        REGLAS: Estilo ejecutivo, clínico, directo. Sin clichés.
        SI SE PIDE UN DOCUMENTO: Estructúralo con Títulos, Introducción, Desarrollo y Conclusiones/Recomendaciones.
        """
        
        res = model.generate_content([system_p, prompt])
        st.session_state.last_response = res.text # Guardamos para la descarga
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
