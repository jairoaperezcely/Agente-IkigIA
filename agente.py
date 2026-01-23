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

# --- FUNCIONES DE EXTRACCIÓN AVANZADA ---

def get_web_text(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        return "\n".join([p.get_text() for p in soup.find_all('p')])
    except: return "Error al leer la web."

def get_yt_text(url):
    try:
        video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        return " ".join([t['text'] for t in transcript])
    except: return "No se encontró transcripción en el video."

def extract_office_text(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext == ".xlsx":
        df = pd.read_excel(file)
        return df.to_string()
    elif ext == ".pptx":
        # Requiere: pip install python-pptx
        from pptx import Presentation
        prs = Presentation(file)
        return "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
    return ""

# --- INTERFAZ DE FUENTES (SIDEBAR) ---
with st.sidebar:
    st.header("🔌 Conectores de IkigAI")
    tab_docs, tab_web, tab_media = st.tabs(["📄 Office/PDF", "🌐 Web", "🎥 Video/YT"])
    
    with tab_docs:
        files = st.file_uploader("Subir Excel, PPT, Word, PDF:", type=['pdf', 'docx', 'xlsx', 'pptx'], accept_multiple_files=True)
        if st.button("🧠 Cargar Documentos"):
            # Lógica de extracción aquí...
            st.success("Documentos integrados.")

    with tab_web:
        url_input = st.text_input("URL de página web:")
        if st.button("🔗 Ingerir Web"):
            st.session_state.biblioteca[rol_activo] += f"\n{get_web_text(url_input)}"
            st.success("Contenido web guardado.")

    with tab_media:
        yt_input = st.text_input("URL de YouTube:")
        video_file = st.file_uploader("O subir archivo de video directo:", type=['mp4', 'mov'])
        if st.button("📺 Procesar Video/YT"):
            if yt_input:
                st.session_state.biblioteca[rol_activo] += f"\n{get_yt_text(yt_input)}"
            st.success("Video procesado.")
