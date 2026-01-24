import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import pandas as pd
import requests
from bs4 import BeautifulSoup
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
    page_title="IkigAI V1.95 - Executive Workstation", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo "Lienzo Zen" (CSS para excelencia visual y móvil)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, h2, h3 { color: #FFFFFF !important; }
    
    /* ELIMINACIÓN DE CAJAS DE MENSAJES */
    [data-testid="stChatMessage"] { 
        background-color: transparent !important; 
        border: none !important; 
        padding-left: 0 !important;
    }
    
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; text-align: justify; }
    .stDownloadButton button, .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; }
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; }
    
    /* CHAT INPUT MINIMALISTA */
    .stChatInputContainer { padding: 20px 0 !important; background-color: transparent !important; border: none !important; }
    .stChatInput textarea { 
        background-color: #1E1F20 !important; border: 1px solid #3C4043 !important; 
        border-radius: 28px !important; color: #E3E3E3 !important; padding: 14px 24px !important; 
    }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Investigador Científico": "Metodología, rigor y APA 7.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión académica, normativa y MD-PhD.",
    "Director de UCI": "Rigor clínico, datos HUN y seguridad.",
    "Consultor Salud Digital": "BID/MinSalud y territorio.",
    "Estratega de Trading": "Gestión de riesgo y SMC."
}

# --- 2. FUNCIONES DE LECTURA Y PERSISTENCIA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])

def exportar_sesion():
    mensajes_finales = []
    for i, msg in enumerate(st.session_state.messages):
        nuevo_msg = msg.copy()
        if msg["role"] == "assistant" and f"edit_{i}" in st.session_state:
            nuevo_msg["content"] = st.session_state[f"edit_{i}"]
        mensajes_finales.append(nuevo_msg)
    data = {"biblioteca": st.session_state.biblioteca, "messages": mensajes_finales, "last_analysis": st.session_state.last_analysis}
    return json.dumps(data, indent=4)

# --- 3. MOTOR DE EXPORTACIÓN (V1.95 - EXCELENCIA TÉCNICA) ---
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def extraer_titulo_dictado(messages, indices_seleccionados):
    if not indices_seleccionados: return "MANUAL TÉCNICO"
    primer_bloque = messages[indices_seleccionados[0]]["content"].split('\n')[:5]
    for linea in primer_bloque:
        if any(x in linea.upper() for x in ["COMO IKIGAI", "DOCTOR", "HOLA"]): continue
        titulo = re.sub(r'^#+\s*', '', linea).strip()
        if len(titulo) > 5: return titulo.upper()
    return "DOCUMENTO ESTRATÉGICO"

def download_word_compilado(indices_seleccionados, messages, role):
    doc = docx.Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(12)
    style.paragraph_format.line_spacing = 1.15
    
    section = doc.sections[0]
    for m in ['left', 'right', 'top', 'bottom']: setattr(section, f'{m}_margin', Inches(1))
    
    titulo_final = extraer_titulo_dictado(messages, indices_seleccionados)
    t = doc.add_heading(titulo_final, 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in t.runs: run.font.color.rgb = RGBColor(0, 32, 96)

    doc.add_paragraph("").add_run()
    autor_p = doc.add_paragraph()
    run_a = autor_p.add_run("Jairo Antonio Pérez Cely")
    run_a.bold = True
    autor_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("Estratega en Salud Digital e Innovación").alignment = 1
    doc.add_paragraph(f"Referencia Técnica | {date.today()}").alignment = 1
    doc.add_paragraph("_" * 65).alignment = 1
    
    for idx in sorted(indices_seleccionados):
        content = messages[idx]["content"]
        for line in content.split('\n'):
            if any(x in line.upper() for x in ["COMO IKIGAI", "DOCTOR"]): continue
            clean = re.sub(r'\*+', '', line).strip()
            if not clean: continue
            if line.startswith('#'):
                h = doc.add_heading(clean, level=min(line.count('#'), 3))
                h.paragraph_format.keep_with_next = True
                for run in h.runs: run.font.name = 'Arial'
            elif line.strip().startswith(('*', '-', '•')):
                p = doc.add_paragraph(re.sub(r'^[\*\-\•]+\s*', '', clean), style='List Bullet')
                p.paragraph_format.left_indent = Inches(0.25)
            else:
                p = doc.add_paragraph(clean)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_page_break()
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "export_pool" not in st.session_state: st.session_state.export_pool = []

# --- 5. BARRA LATERAL (CONTROL Y CONTEXTO) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧬 IKIGAI</h2>", unsafe_allow_html=True)
    
    st.markdown("<div class='section-tag'>SESIÓN</div>", unsafe_allow_html=True)
    if st.button("🗑️ Reiniciar"):
        st.session_state.messages = []; st.session_state.export_pool = []; st.rerun()
    
    st.divider()
    rol_activo = st.radio("Rol activo:", options=list(ROLES.keys()))
    
    if st.session_state.export_pool:
        st.divider()
        st.markdown(f"<div class='section-tag'>ENTREGABLES ({len(st.session_state.export_pool)} BLOQUES)</div>", unsafe_allow_html=True)
        word_data = download_word_compilado(st.session_state.export_pool, st.session_state.messages, rol_activo)
        st.download_button("📄 Generar Word", data=word_data, file_name=f"Manual_{date.today()}.docx")

    st.divider()
    st.markdown("<div class='section-tag'>FUENTES DE CONTEXTO</div>", unsafe_allow_html=True)
    up = st.file_uploader("Subir PDF/Word:", type=['pdf', 'docx'], accept_multiple_files=True)
    if up and st.button("🧠 PROCESAR ARCHIVOS"):
        raw_text = ""
        for f in up: raw_text += get_pdf_text(f) if f.type == "application/pdf" else get_docx_text(f)
        with st.spinner("Analizando contexto..."):
            model = genai.GenerativeModel('gemini-2.5-flash')
            res = model.generate_content(f"Resume datos clave para manual de telesalud: {raw_text[:50000]}")
            st.session_state.biblioteca[rol_activo] = res.text
            st.success("Contexto actualizado.")

# --- 6. WORKSTATION (INTERFAZ ZEN Y EDICIÓN) ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            is_selected = i in st.session_state.export_pool
            if st.checkbox(f"📥 Incluir en Manual", key=f"sel_{i}", value=is_selected):
                if i not in st.session_state.export_pool: st.session_state.export_pool.append(i)
            else:
                if i in st.session_state.export_pool: st.session_state.export_pool.remove(i)
            
            with st.expander("📝 EDITAR ESTE BLOQUE"):
                texto_editado = st.text_area("Modifique aquí:", value=msg["content"], height=300, key=f"edit_{i}")
                if st.button("✅ Guardar Cambios", key=f"save_{i}"):
                    st.session_state.messages[i]["content"] = texto_editado
                    st.success("Cambio guardado.")

if pr := st.chat_input("¿Qué sección diseñamos ahora, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            sys_context = f"Rol: {rol_activo}. Estilo clínico/ejecutivo. APA 7. Autor: Jairo Pérez Cely."
            lib_context = st.session_state.biblioteca.get(rol_activo, '')[:40000]
            response = model.generate_content([sys_context, f"Contexto: {lib_context}", pr])
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
