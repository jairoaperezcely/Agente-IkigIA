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
    page_title="IkigAI V1.52 - Strategic Intelligence Center", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS de Alta Costura Digital: Minimalismo, Tipografía y Contraste Suave
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

    /* Reset General */
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #050505 !important;
        font-family: 'Inter', sans-serif !important;
        color: #E0E0E0 !important;
    }

    /* Sidebar con efecto Glassmorphism */
    [data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        border-right: 1px solid #1A1A1A !important;
        padding-top: 2rem;
    }

    /* Títulos y Labels */
    h1, h2, h3, label, p {
        color: #FFFFFF !important;
        font-weight: 300 !important;
    }

    /* Botones de Descarga: Estilo Minimalista Premium */
    .stDownloadButton button {
        width: 100%;
        border-radius: 4px;
        height: 3em;
        background-color: transparent !important;
        color: #00A3FF !important;
        border: 1px solid #00A3FF !important;
        font-size: 14px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: 0.4s all ease;
    }
    .stDownloadButton button:hover {
        background-color: #00A3FF !important;
        color: #000000 !important;
        box-shadow: 0 0 20px rgba(0, 163, 255, 0.4);
    }

    /* Botón de Reinicio: Sutil y Elegante */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 4px;
        background-color: #1A1A1A !important;
        color: #666666 !important;
        border: 1px solid #333333 !important;
        font-size: 12px;
    }
    div.stButton > button:first-child:hover {
        border-color: #FF4B4B !important;
        color: #FF4B4B !important;
    }

    /* Corrección Definitiva File Uploader (Zona Minimalista) */
    [data-testid="stFileUploadDropzone"] {
        background-color: #0F0F0F !important;
        border: 1px dashed #333333 !important;
        border-radius: 8px !important;
    }
    [data-testid="stFileUploadDropzone"] div div {
        color: #666666 !important;
    }

    /* Estilo de los Chat Messages */
    [data-testid="stChatMessage"] {
        background-color: #0F0F0F !important;
        border-radius: 10px !important;
        border: 1px solid #1A1A1A !important;
        margin-bottom: 10px;
    }

    /* Tabs del Sidebar */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        color: #666666 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00A3FF !important;
        border-bottom: 2px solid #00A3FF !important;
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
    except: return "Error en web."
def get_yt_text(url):
    try:
        v_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        return " ".join([t['text'] for t in YouTubeTranscriptApi.get_transcript(v_id, languages=['es', 'en'])])
    except: return "Error en YouTube."

# --- 3. MOTOR DE EXPORTACIÓN OFFICE ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Análisis Estratégico: {role}', 0)
    doc.add_paragraph(f"Generado por IkigAI - {date.today()}").italic = True
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = role.upper()
    slide.placeholders[1].text = f"Estrategia Ejecutiva\n{date.today()}"
    sections = [p for p in content.split('\n\n') if len(p.strip()) > 30]
    for i, p in enumerate(sections[:10]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Pilar Estratégico {i+1}"; slide.placeholders[1].text = p[:550]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "temp_image" not in st.session_state: st.session_state.temp_image = None

# --- 5. BARRA LATERAL (DISEÑO MINIMALISTA) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Universidad_Nacional_de_Colombia_Logo.svg/1200px-Universidad_Nacional_de_Colombia_Logo.svg.png", width=50)
    st.markdown("<h2 style='text-align: center; font-size: 22px; letter-spacing: 2px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    if st.button("RESET ENGINE"):
        st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
        st.session_state.messages = []
        st.session_state.last_analysis = ""
        st.session_state.temp_image = None
        st.rerun()

    st.divider()
    st.markdown("<p style='font-size: 12px; color: #666;'>PERFIL ESTRATÉGICO</p>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    st.session_state.rol_actual = rol_activo
    
    if st.session_state.last_analysis:
        st.divider()
        st.markdown("<p style='font-size: 12px; color: #666;'>ENTREGABLES OFFICE</p>", unsafe_allow_html=True)
        st.download_button("WORD (APA 7)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("POWERPOINT", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

    st.divider()
    st.markdown("<p style='font-size: 12px; color: #666;'>FUENTES DE DATOS</p>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["DOC", "LINK", "IMG"])
    with t1:
        up = st.file_uploader("Cargar:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("ANALIZAR DOCUMENTOS", use_container_width=True):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Analizado.")
    with t2:
        uw = st.text_input("URL Web:", placeholder="https://")
        uy = st.text_input("URL YouTube:", placeholder="https://")
        if st.button("CONECTAR NODOS", use_container_width=True):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Conectado.")
    with t3:
        img_f = st.file_uploader("Imagen:", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f:
            st.session_state.temp_image = Image.open(img_f); st.image(img_f)

# --- 6. PANEL CENTRAL ---
st.markdown(f"<h3 style='color: #00A3FF !important;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): 
        st.markdown(msg["content"])

if pr := st.chat_input("¿Qué diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, directo, ejecutivo. Citas APA 7."
        
        content_to_send = [sys_context, f"Contexto acumulado: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: content_to_send.append(st.session_state.temp_image)
        
        response = model.generate_content(content_to_send)
        st.session_state.last_analysis = response.text
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
