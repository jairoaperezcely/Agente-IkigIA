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

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(
    page_title="IkigAI V1.55 - Final Executive Hub", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Final: Aislamiento total y Legibilidad Extrema
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

    /* FONDO GENERAL */
    .stApp {
        background-color: #000000 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* BARRA LATERAL */
    [data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        border-right: 1px solid #1A1A1A !important;
    }
    
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1, h2, h3 {
        color: #FFFFFF !important;
    }

    /* CHAT: CONTRASTE MÁXIMO */
    [data-testid="stChatMessage"] {
        background-color: #050505 !important;
        border: 1px solid #1A1A1A !important;
    }

    .stMarkdown p, .stMarkdown li {
        color: #FFFFFF !important;
        font-size: 16px !important;
        line-height: 1.7 !important;
    }

    /* REFERENCIAS APA 7: Legibilidad Garantizada (Texto en Cian/Azul Claro) */
    blockquote {
        border-left: 4px solid #00E6FF !important;
        background-color: #0D1117 !important;
        padding: 15px !important;
        margin: 15px 0 !important;
    }
    blockquote p {
        color: #58A6FF !important;
        font-style: italic !important;
        font-size: 14px !important;
    }

    /* BOTONES DE EXPORTACIÓN */
    .stDownloadButton button {
        width: 100%;
        border-radius: 6px;
        background-color: transparent !important;
        color: #00E6FF !important;
        border: 1px solid #00E6FF !important;
        font-weight: 600;
    }
    .stDownloadButton button:hover {
        background-color: #00E6FF !important;
        color: #000000 !important;
    }

    /* FIX PARA FILE UPLOADER (Fondo Oscuro) */
    [data-testid="stFileUploadDropzone"] {
        background-color: #0A0A0A !important;
        border: 1px dashed #333 !important;
    }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y sostenibilidad.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión y normativa Medicina UNAL.",
    "Director de UCI": "Rigor clínico y datos HUN.",
    "Investigador Científico": "Metodología y APA 7.",
    "Consultor Salud Digital": "BID/MinSalud y territorio.",
    "Professor Universitario": "Pedagogía médica disruptiva.",
    "Estratega de Trading": "Gestión de riesgo y SMC."
}

# --- 2. FUNCIONES DE LECTURA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_excel_text(f): return pd.read_excel(f).to_string()
def get_web_text(url):
    try:
        r = requests.get(url, timeout=10)
        return "\n".join([p.get_text() for p in BeautifulSoup(r.text, 'html.parser').find_all('p')])
    except: return ""

# --- 3. EXPORTACIÓN OFFICE ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Informe IkigAI: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()}").italic = True
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    # Corrección de la lógica de creación de slides
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    # Portada
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = role.upper()
    slide.placeholders[1].text = f"Análisis Estratégico - {date.today()}"
    # Contenido
    for i, p in enumerate(points[:8]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje {i+1}"
        slide.placeholders[1].text = p[:550]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    
    if st.button("🗑️ REINICIAR SESIÓN"):
        st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
        st.session_state.messages = []
        st.session_state.last_analysis = ""
        st.rerun()

    st.divider()
    st.subheader("🎯 Perfil")
    rol_activo = st.radio("Selección:", options=list(ROLES.keys()))
    
    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 Exportar")
        st.download_button("📄 WORD (APA 7)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"Report_{rol_activo}.docx")
        st.download_button("📊 POWERPOINT", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"Deck_{rol_activo}.pptx")

    st.divider()
    st.subheader("🔌 Datos")
    t1, t2, t3 = st.tabs(["DOC", "URL", "IMG"])
    with t1:
        up = st.file_uploader("Cargar archivos:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 PROCESAR", use_container_width=True):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Cargado.")
    with t2:
        uw = st.text_input("URL:", placeholder="https://")
        if st.button("🔗 CONECTAR", use_container_width=True):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            st.success("Link OK.")
    with t3:
        img_f = st.file_uploader("Imagen:", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f:
            st.session_state.temp_image = Image.open(img_f); st.image(img_f)

# --- 6. PANEL CENTRAL ---
st.markdown(f"<h3 style='color: #00A3FF;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("¿Qué analizamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, directo. APA 7 obligatorio."
        response = model.generate_content([sys_context, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr])
        st.session_state.last_analysis = response.text
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
