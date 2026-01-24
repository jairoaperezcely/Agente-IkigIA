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
from pptx.util import Inches, Pt
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(
    page_title="IkigAI V1.74 - Pure Executive Hub", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS: Zen Minimalista con Contraste Quirúrgico
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, h2, h3 { color: #FFFFFF !important; }
    [data-testid="stChatMessage"] { background-color: #050505 !important; border: 1px solid #1A1A1A !important; }
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    blockquote { border-left: 4px solid #00E6FF !important; background-color: #0D1117 !important; padding: 15px !important; margin: 15px 0 !important; }
    blockquote p { color: #58A6FF !important; font-style: italic !important; font-size: 14px !important; }
    .stDownloadButton button, .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; }
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y sostenibilidad administrativa.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión académica, normativa y MD-PhD.",
    "Director de UCI": "Rigor clínico, datos HUN y seguridad.",
    "Investigador Científico": "Metodología, rigor y APA 7.",
    "Consultor Salud Digital": "BID/MinSalud y territorio.",
    "Professor Universitario": "Pedagogía médica disruptiva.",
    "Estratega de Trading": "Gestión de riesgo y SMC."
}

# --- 2. FUNCIONES DE LECTURA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_excel_text(f): return pd.read_excel(f).to_string()

# --- 3. MOTOR DE LIMPIEZA Y EXPORTACIÓN ---
def clean_markdown(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def download_word(content, role):
    doc = docx.Document()
    section = doc.sections[0]
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    header = doc.add_heading(f'INFORME ESTRATÉGICO: {role.upper()}', 0)
    header.alignment = 1
    doc.add_paragraph(f"Fecha: {date.today()} | IkigAI V1.74 Executive Analysis")
    doc.add_paragraph("_" * 50)
    lines = content.split('\n')
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        if clean_line.startswith('#'):
            level = clean_line.count('#')
            doc.add_heading(clean_line.replace('#', '').strip(), level=min(level, 3))
        elif clean_line.startswith(('*', '-', '•')):
            doc.add_paragraph(clean_line[1:].strip(), style='List Bullet')
        else:
            p = doc.add_paragraph(clean_line)
            p.alignment = 3
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    segments = [clean_markdown(s) for s in re.split(r'\n|\. ', content) if len(s.strip()) > 25]
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = role.upper()
    slide.placeholders[1].text = f"Estrategia Ejecutiva IkigAI\n{date.today()}"
    for i, segment in enumerate(segments[:15]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje {i+1}"
        body = slide.placeholders[1]
        body.text = (segment[:447] + '...') if len(segment) > 450 else segment
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    if st.button("🗑️ REINICIAR"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    st.divider()
    st.markdown("<div class='section-tag'>PERFIL ESTRATÉGICO</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    if st.session_state.get("last_analysis"):
        st.divider()
        st.markdown("<div class='section-tag'>EXPORTAR ENTREGABLES</div>", unsafe_allow_html=True)
        st.download_button("📄 Word", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"Report_{rol_activo}.docx")
        st.download_button("📊 Powerpoint", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"Deck_{rol_activo}.pptx")

    st.divider()
    st.markdown("<div class='section-tag'>FUENTES DE DATOS</div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["DOC", "URL", "IMG"])
    with t1:
        up = st.file_uploader("Upload:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 PROCESAR", use_container_width=True):
            raw_text = ""
            for f in up:
                if f.type == "application/pdf": raw_text += get_pdf_text(f)
                elif "word" in f.type: raw_text += get_docx_text(f)
                else: raw_text += get_excel_text(f)
            
            with st.spinner("Refinando contexto estratégico..."):
                refiner = genai.GenerativeModel('gemini-1.5-flash')
                summary_prompt = f"Actúa como Secretario Técnico. Extrae solo datos duros, métricas y decisiones estratégicas. Elimina ruido. Contexto: {raw_text[:40000]}"
                st.session_state.biblioteca[rol_activo] = refiner.generate_content(summary_prompt).text
            st.success("Contexto Refinado.")
    with t2:
        uw = st.text_input("Link:", placeholder="https://")
        if st.button("🔗 CONECTAR", use_container_width=True):
            r = requests.get(uw, timeout=10)
            st.session_state.biblioteca[rol_activo] += BeautifulSoup(r.text, 'html.parser').get_text()
            st.success("Conectado.")
    with t3:
        img_f = st.file_uploader("Image:", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f: st.session_state.temp_image = Image.open(img_f); st.image(img_f)

# --- 6. PANEL CENTRAL ---
st.markdown(f"<h3 style='color: #00A3FF;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            with st.expander("📥 Portapapeles (Copiar texto limpio)"):
                st.code(msg["content"], language=None)

if pr := st.chat_input("¿Qué diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, directo, ejecutivo. APA 7."
        lib_context = st.session_state.biblioteca.get(rol_activo, '')[:500000]
        response = model.generate_content([sys_context, f"Contexto: {lib_context}", pr])
        st.session_state.last_analysis = response.text
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
