import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import requests
import os
from datetime import date
from io import BytesIO

# --- 1. CONFIGURACIÓN E IDENTIDADES ---
st.set_page_config(page_title="IkigAI V1.9 - Liderazgo Integral", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

# Diccionario de Roles Final (8 Pilares)
ROLES = {
    "Coach de Alto Desempeño": "Foco en ROI cognitivo, bienestar y eliminación de procastinación oculta.",
    "Director Centro Telemedicina": "Estratega en Salud Digital e IA. Innovación y Hospital Virtual.",
    "Vicedecano Académico": "Gestión administrativa UNAL, normativa y liderazgo institucional.",
    "Investigador Científico": "Metodología, revisión sistemática, redacción científica y medicina basada en evidencia.",
    "Director de UCI": "Rigor clínico, seguridad del paciente en el HUN y datos críticos.",
    "Consultor Salud Digital": "Estratega BID/MinSalud. Foco en territorio e interculturalidad.",
    "Profesor Universitario": "Pedagogía disruptiva y mentoría en educación médica.",
    "Estratega de Trading": "Análisis técnico, gestión de riesgo y psicología de la decisión."
}

# --- 2. FUNCIONES DE LECTURA (PDF, DOCX, EXCEL, WEB, YT) ---
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages])

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def get_excel_text(xlsx_file):
    df = pd.read_excel(xlsx_file)
    return f"CONTENIDO EXCEL:\n{df.to_string()}"

def get_web_text(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        return f"CONTENIDO WEB ({url}):\n" + "\n".join([p.get_text() for p in soup.find_all('p')])
    except: return "Error al leer la web."

def get_yt_text(url):
    try:
        video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        return f"TRANSCRIPCIÓN YOUTUBE:\n" + " ".join([t['text'] for t in transcript])
    except: return "No se encontró transcripción."

# --- 3. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state:
    st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []

# --- 4. BARRA LATERAL: CONECTORES DE LECTURA ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    
    st.divider()
    st.subheader(f"🔌 Fuentes para {rol_activo}")
    
    tab_files, tab_links = st.tabs(["📄 Archivos", "🔗 Links"])
    
    with tab_files:
        up_files = st.file_uploader("Cargar PDF, Word, Excel:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer Documentos"):
            for f in up_files:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "document" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Documentos leídos.")

    with tab_links:
        url_w = st.text_input("URL Web:")
        url_y = st.text_input("URL YouTube:")
        if st.button("🌐 Leer Links"):
            if url_w: st.session_state.biblioteca[rol_activo] += get_web_text(url_w)
            if url_y: st.session_state.biblioteca[rol_activo] += get_yt_text(url_y)
            st.success("Fuentes externas leídas.")

    if st.button("🗑️ Reiniciar Sesión"):
        st.session_state.messages = []
        st.rerun()

# --- 5. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

# Módulo de ROI Cognitivo
with st.expander("🚀 Análisis de Prioridades"):
    tareas = st.text_area("Objetivos de hoy:", placeholder="Ej: Revisar metodología del estudio de tele-UCI...")
    if st.button("Calcular ROI"):
        # Se activa mediante el prompt principal para usar todo el contexto leído
        pass

# Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Escriba su instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-1.5-pro')
        system_p = f"""
        IDENTIDAD: Actúa como IkigAI en modo {rol_activo}. {ROLES[rol_activo]}
        CONTENIDO LEÍDO PARA ESTE ROL: {st.session_state.biblioteca[rol_activo][:500000]}
        REGLAS: Estilo ejecutivo, clínico, directo. Sin clichés. Cita APA 7.
        """
        res = model.generate_content([system_p, prompt])
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
