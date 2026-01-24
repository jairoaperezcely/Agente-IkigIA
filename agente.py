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
    page_title="IkigAI V1.83 - Executive Workstation", 
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
    data = {
        "biblioteca": st.session_state.biblioteca, 
        "messages": mensajes_finales, 
        "last_analysis": st.session_state.last_analysis
    }
    return json.dumps(data, indent=4)

def cargar_sesion(json_data):
    data = json.loads(json_data)
    st.session_state.biblioteca = data["biblioteca"]
    st.session_state.messages = data["messages"]
    st.session_state.last_analysis = data["last_analysis"]

# --- 3. MOTOR DE EXPORTACIÓN ---
def clean_markdown(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

def download_word(content, role):
    doc = docx.Document()
    section = doc.sections[0]
    section.left_margin = Inches(1); section.right_margin = Inches(1)
    header = doc.add_heading(f'INFORME ESTRATÉGICO: {role.upper()}', 0)
    header.alignment = 1
    doc.add_paragraph(f"Fecha: {date.today()} | IkigAI V1.83 Executive Hub")
    doc.add_paragraph("_" * 50)
    for line in content.split('\n'):
        clean_line = line.strip()
        if not clean_line: continue
        if clean_line.startswith('#'):
            doc.add_heading(clean_line.replace('#', '').strip(), level=min(clean_line.count('#'), 3))
        elif clean_line.startswith(('*', '-', '•')):
            doc.add_paragraph(clean_line[1:].strip(), style='List Bullet')
        else:
            p = doc.add_paragraph(clean_line); p.alignment = 3
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
        slide.placeholders[1].text = (segment[:447] + '...') if len(segment) > 450 else segment
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL (Panel de Control) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ REINICIAR"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    with col2:
        # Botón de Guardado siempre visible
        st.download_button(
            label="💾 GUARDAR SESION",
            data=exportar_sesion(),
            file_name=f"IkigAI_Turno_{date.today()}.json",
            mime="application/json",
            key="save_session_v183"
        )
    
    archivo_memoria = st.file_uploader("RECUPERAR TURNO:", type=['json'], label_visibility="collapsed")
    if archivo_memoria:
        if st.button("🔌 RECONECTAR SESION", use_container_width=True):
            cargar_sesion(archivo_memoria.getvalue().decode("utf-8"))
            st.success("Cerebro reconectado.")
            st.rerun()

    st.divider()
    st.markdown("<div class='section-tag'>PERFIL ESTRATÉGICO</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol activo:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    if st.session_state.get("last_analysis"):
        st.divider()
        st.markdown("<div class='section-tag'>EXPORTAR ENTREGABLES</div>", unsafe_allow_html=True)
        st.download_button("📄 Word", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"Report_{rol_activo}.docx")
        st.download_button("📊 PPT", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"Deck_{rol_activo}.pptx")

    st.divider()
    st.markdown("<div class='section-tag'>FUENTES DE CONTEXTO</div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["DOC", "URL", "IMG"])
    with t1:
        up = st.file_uploader("Subir archivos:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 PROCESAR", use_container_width=True):
            raw_text = ""
            for f in up:
                if f.type == "application/pdf": raw_text += get_pdf_text(f)
                elif "word" in f.type: raw_text += get_docx_text(f)
                else: raw_text += get_excel_text(f)
            with st.spinner("Analizando fuentes..."):
                refiner = genai.GenerativeModel('gemini-1.5-flash')
                summary_prompt = f"Actúa como Secretario Técnico. Extrae datos clave. Contexto: {raw_text[:40000]}"
                st.session_state.biblioteca[rol_activo] = refiner.generate_content(summary_prompt).text
            st.success("Contexto listo.")
    with t2:
        uw = st.text_input("URL:", placeholder="https://")
        if st.button("🔗 CONECTAR", use_container_width=True):
            r = requests.get(uw, timeout=10)
            st.session_state.biblioteca[rol_activo] += BeautifulSoup(r.text, 'html.parser').get_text()
            st.success("Web conectada.")
    with t3:
        img_f = st.file_uploader("Imagen:", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f: st.session_state.temp_image = Image.open(img_f); st.image(img_f)

# --- 6. PANEL CENTRAL: WORKSTATION ---
st.markdown(f"<h3 style='color: #00A3FF;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(msg["role"]):
        # 1. LECTURA SIEMPRE DISPONIBLE (Markdown Limpio)
        st.markdown(msg["content"])
        
        if msg["role"] == "assistant":
            # 2. ESPACIO DE TRABAJO (Expander con Copiar y Editar)
            with st.expander("🛠️ GESTIONAR ENTREGABLE", expanded=False):
                t_copy, t_edit = st.tabs(["📋 COPIAR", "📝 EDITAR"])
                
                with t_copy:
                    st.code(msg["content"], language=None)
                    st.caption("Icono superior derecho para copiar.")
                
                with t_edit:
                    texto_editado = st.text_area(
                        "Editor ejecutivo:", 
                        value=msg["content"], 
                        height=450, 
                        key=f"edit_{i}",
                        label_visibility="collapsed"
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✅ FIJAR CAMBIOS", key=f"save_{i}", use_container_width=True):
                        st.session_state.last_analysis = texto_editado
                        st.toast("✅ Sincronizado para exportación.")
        st.markdown("---")

if pr := st.chat_input("¿Qué diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        # MOTOR ACTUALIZADO: Gemini 2.5 Flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, ejecutivo. APA 7."
        lib_context = st.session_state.biblioteca.get(rol_activo, '')[:500000]
        response = model.generate_content([sys_context, f"Contexto: {lib_context}", pr])
        st.session_state.last_analysis = response.text
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
