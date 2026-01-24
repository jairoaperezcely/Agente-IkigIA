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
import json

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(
    page_title="IkigAI V1.86 - Executive Workstation", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Zen: Contraste Quirúrgico y Ergonomía Móvil
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, h2, h3 { color: #FFFFFF !important; }
    [data-testid="stChatMessage"] { background-color: #050505 !important; border: 1px solid #1A1A1A !important; }
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    .stDownloadButton button, .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; }
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; }
    .stExpander { border: 1px solid #1A1A1A !important; background-color: #050505 !important; border-radius: 8px !important; }
    textarea { background-color: #0D1117 !important; color: #FFFFFF !important; border: 1px solid #00E6FF !important; font-family: 'Courier New', monospace !important; font-size: 14px !important; }
    /* Estilo Checkbox de Selección */
    .stCheckbox { background-color: #111; padding: 5px; border-radius: 5px; border: 1px solid #333; margin-top: 10px; }
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

# --- 2. FUNCIONES DE LECTURA Y PERSISTENCIA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_excel_text(f): return pd.read_excel(f).to_string()

def exportar_sesion():
    mensajes_finales = []
    for i, msg in enumerate(st.session_state.messages):
        nuevo_msg = msg.copy()
        if msg["role"] == "assistant" and f"edit_{i}" in st.session_state:
            nuevo_msg["content"] = st.session_state[f"edit_{i}"]
        mensajes_finales.append(nuevo_msg)
    data = {"biblioteca": st.session_state.biblioteca, "messages": mensajes_finales, "last_analysis": st.session_state.last_analysis}
    return json.dumps(data, indent=4)

def cargar_sesion(json_data):
    data = json.loads(json_data)
    st.session_state.biblioteca = data["biblioteca"]
    st.session_state.messages = data["messages"]
    st.session_state.last_analysis = data["last_analysis"]

# --- 3. MOTOR DE EXPORTACIÓN COMPILADA ---
def download_word_compilado(indices_seleccionados, messages, role):
    doc = docx.Document()
    section = doc.sections[0]
    section.left_margin = Inches(1); section.right_margin = Inches(1)
    
    header = doc.add_heading(f'MANUAL ACADÉMICO: {role.upper()}', 0)
    header.alignment = 1
    doc.add_paragraph(f"Fecha: {date.today()} | Compilado IkigAI V1.86")
    doc.add_paragraph("_" * 50)
    
    for idx in indices_seleccionados:
        content = messages[idx]["content"]
        # Limpieza de asteriscos
        for line in content.split('\n'):
            clean_line = re.sub(r'\*+', '', line).strip()
            if not clean_line: continue
            
            if line.startswith('#'):
                level = line.count('#')
                doc.add_heading(clean_line, level=min(level, 3))
            elif line.startswith(('*', '-', '•')):
                doc.add_paragraph(clean_line.lstrip('*-• ').strip(), style='List Bullet')
            else:
                p = doc.add_paragraph(clean_line)
                p.alignment = 3
        # Salto de página entre bloques para rigor de manual
        doc.add_page_break()
    
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "export_pool" not in st.session_state: st.session_state.export_pool = []

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    st.divider()
    st.markdown("<div class='section-tag'>SESIÓN</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reiniciar"):
            st.session_state.messages = []
            st.session_state.export_pool = []
            st.rerun()
    with col2:
        st.download_button(label="💾 Guardar", data=exportar_sesion(), file_name=f"IkigAI_Turno_{date.today()}.json", mime="application/json")
    
    archivo_memoria = st.file_uploader("RECUPERAR TURNO:", type=['json'], label_visibility="collapsed")
    if archivo_memoria:
        if st.button("🔌 RECONECTAR", use_container_width=True):
            cargar_sesion(archivo_memoria.getvalue().decode("utf-8"))
            st.rerun()

    st.divider()
    st.markdown("<div class='section-tag'>PERFIL ESTRATÉGICO</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol activo:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    # Exportación Compilada
    if st.session_state.export_pool:
        st.divider()
        st.markdown(f"<div class='section-tag'>COMPILADOR ({len(st.session_state.export_pool)} BLOQUES)</div>", unsafe_allow_html=True)
        word_data = download_word_compilado(st.session_state.export_pool, st.session_state.messages, rol_activo)
        st.download_button("📄 Exportar Manual (Word)", data=word_data, file_name=f"Manual_Amazonia_{rol_activo}.docx", use_container_width=True)

    st.divider()
    st.markdown("<div class='section-tag'>FUENTES</div>", unsafe_allow_html=True)
    up = st.file_uploader("Subir DOCS:", type=['pdf', 'docx'], accept_multiple_files=True, label_visibility="collapsed")
    if st.button("🧠 PROCESAR", use_container_width=True):
        raw_text = ""
        for f in up:
            if f.type == "application/pdf": raw_text += get_pdf_text(f)
            else: raw_text += get_docx_text(f)
        try:
            refiner = genai.GenerativeModel('gemini-2.5-flash')
            summary_prompt = f"Actúa como Secretario Técnico. Extrae datos clave. Contexto: {raw_text[:40000]}"
            st.session_state.biblioteca[rol_activo] = refiner.generate_content(summary_prompt).text
            st.success("Contexto integrado.")
        except:
            st.session_state.biblioteca[rol_activo] = raw_text[:30000]

# --- 6. PANEL CENTRAL: SELECCIÓN MULTIPLE PARA EXPORTACIÓN ---
st.markdown(f"<h3 style='color: #00A3FF;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

# Inicializar pool de exportación si no existe
if "export_pool" not in st.session_state:
    st.session_state.export_pool = []

for i, msg in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if msg["role"] == "assistant":
            # Checkbox para incluir en el Word final
            seleccionar = st.checkbox("📥 Incluir en Manual (Word)", key=f"sel_{i}")
            if seleccionar:
                if i not in st.session_state.export_pool:
                    st.session_state.export_pool.append(i)
            else:
                if i in st.session_state.export_pool:
                    st.session_state.export_pool.remove(i)

            with st.expander("🛠️ GESTIONAR ENTREGABLE", expanded=False):
                # ... (resto de la lógica de copiar/editar que ya tiene)
