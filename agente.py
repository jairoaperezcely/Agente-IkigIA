import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
from datetime import date
from pptx import Presentation
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(
    page_title="IkigAI V1.48 - Executive Design Center", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS para modo oscuro, visibilidad y botones
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h1, h2, h3 {
        color: #ffffff !important;
    }

    .stDownloadButton button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #1f2937;
        color: #00d4ff !important;
        border: 1px solid #00d4ff;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    /* Botón de Reinicio Rojo */
    .stButton button[kind="secondary"] {
        width: 100%;
        background-color: #441111;
        color: #ff4b4b;
        border: 1px solid #ff4b4b;
    }
    .stButton button[kind="secondary"]:hover {
        background-color: #ff4b4b;
        color: white;
    }

    button[data-baseweb="tab"] { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y eliminación de procastinación.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión y normativa Facultad de Medicina UNAL.",
    "Director de UCI": "Rigor clínico y datos en el HUN.",
    "Investigador Científico": "Metodología y redacción científica (APA 7).",
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Professor Universitario": "Pedagogía disruptiva y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado."
}

# --- 2. FUNCIONES DE LECTURA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_excel_text(f): return pd.read_excel(f).to_string()
def get_web_text(url):
    try:
        r = requests.get(url, timeout=10)
        return "\n".join([p.get_text() for p in BeautifulSoup(r.text, 'html.parser').find_all('p')])
    except: return "Error en web."
def get_yt_text(url):
    try:
        v_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        return " ".join([t['text'] for t in YouTubeTranscriptApi.get_transcript(v_id, languages=['es', 'en'])])
    except: return "Error en YouTube."

# --- 3. MOTOR DE EXPORTACIÓN ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Entregable IkigAI: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()} | APA 7").italic = True
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Estrategia {role.upper()}"
    slide.placeholders[1].text = f"IkigAI Engine - {date.today()}"
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    for i, p in enumerate(points[:10]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje {i+1}"; slide.placeholders[1].text = p[:500]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA E INICIALIZACIÓN ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "temp_image" not in st.session_state: st.session_state.temp_image = None

def reset_engine():
    st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
    st.session_state.messages = []
    st.session_state.last_analysis = ""
    st.session_state.temp_image = None
    st.rerun()

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Universidad_Nacional_de_Colombia_Logo.svg/1200px-Universidad_Nacional_de_Colombia_Logo.svg.png", width=60)
    st.title("🧬 IkigAI Engine")
    
    st.subheader("🎯 Perfil Estratégico")
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    st.session_state.rol_actual = rol_activo
    
    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 Exportar")
        st.download_button("📄 Word (APA 7)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 PowerPoint", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

    st.divider()
    st.subheader("🔌 Fuentes")
    tab_files, tab_links, tab_img = st.tabs(["📄 Doc", "🔗 Link", "🖼️ Img"])
    with tab_files:
        up = st.file_uploader("Cargar:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 Procesar", use_container_width=True):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Listo.")
    with tab_links:
        uw = st.text_input("URL Web:", placeholder="https://")
        uy = st.text_input("YouTube:", placeholder="https://")
        if st.button("🌐 Conectar", use_container_width=True):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Conectado.")
    with tab_img:
        img_f = st.file_uploader("Imagen:", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f:
            st.session_state.temp_image = Image.open(img_f); st.image(img_f)

    st.divider()
    if st.button("🗑️ Reiniciar Sesión", kind="secondary", use_container_width=True):
        reset_engine()

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("¿Qué diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, directo. APA 7."
        content_to_send = [sys_context, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: content_to_send.append(st.session_state.temp_image)
        response = model.generate_content(content_to_send)
        st.session_state.last_analysis = response.text
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
