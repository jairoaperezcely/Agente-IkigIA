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
    page_title="IkigAI V1.53 - High Contrast Hub", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS V1.53: Contraste Máximo y Legibilidad de Referencias
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

    /* Fondo Negro Absoluto para Contraste */
    .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #000000 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Texto del Chat: Blanco Puro para Legibilidad */
    .stMarkdown, p, li {
        color: #FFFFFF !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
    }

    /* Resalte Específico para Referencias y Citas (APA 7) */
    blockquote {
        border-left: 3px solid #00A3FF !important;
        background-color: #111111 !important;
        color: #00D4FF !important;
        padding: 10px 20px !important;
        margin: 10px 0px !important;
    }

    /* Sidebar con Alto Contraste */
    [data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        border-right: 1px solid #333333 !important;
    }
    
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    /* Botones Neon de Descarga */
    .stDownloadButton button {
        width: 100%;
        border-radius: 6px;
        background-color: #000000 !important;
        color: #00A3FF !important;
        border: 1px solid #00A3FF !important;
        font-weight: 600;
    }
    .stDownloadButton button:hover {
        background-color: #00A3FF !important;
        color: #000000 !important;
    }

    /* Reset Button */
    div.stButton > button:first-child {
        width: 100%;
        background-color: #1A1A1A !important;
        color: #FF4B4B !important;
        border: 1px solid #FF4B4B !important;
    }

    /* File Uploader Dark Fix */
    [data-testid="stFileUploadDropzone"] {
        background-color: #0A0A0A !important;
        border: 1px dashed #00A3FF !important;
    }
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
    except: return "Error."
def get_yt_text(url):
    try:
        v_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        return " ".join([t['text'] for t in YouTubeTranscriptApi.get_transcript(v_id, languages=['es', 'en'])])
    except: return "Error."

# --- 3. EXPORTACIÓN ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Informe Estratégico: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()} | APA 7").italic = True
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = role.upper()
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    for i, p in enumerate(points[:8]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje {i+1}"; slide.placeholders[1].text = p[:500]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IKIGAI")
    if st.button("RESET ENGINE"):
        st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
        st.session_state.messages = []
        st.session_state.last_analysis = ""
        st.rerun()

    st.divider()
    rol_activo = st.radio("PERFIL ACTIVO:", options=list(ROLES.keys()))
    
    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 EXPORTAR")
        st.download_button("WORD (APA 7)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("POWERPOINT", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

    st.divider()
    st.subheader("🔌 FUENTES")
    t1, t2, t3 = st.tabs(["DOC", "URL", "IMG"])
    with t1:
        up = st.file_uploader("Cargar:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("PROCESAR DOCS", use_container_width=True):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Analizado.")
    with t2:
        uw = st.text_input("Web:", placeholder="https://")
        if st.button("CONECTAR", use_container_width=True):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            st.success("Conectado.")
    with t3:
        img_f = st.file_uploader("Imagen:", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f: st.session_state.temp_image = Image.open(img_f); st.image(img_f)

# --- 6. PANEL CENTRAL ---
st.markdown(f"<h2 style='color: #00A3FF;'>IkigAI Hub: {rol_activo}</h2>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("¿Instrucción estratégica, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, ejecutivo. APA 7 obligatorio."
        response = model.generate_content([sys_context, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr])
        st.session_state.last_analysis = response.text
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
