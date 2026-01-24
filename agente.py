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

# --- 1. CONFIGURACIÓN E IDENTIDAD (OPTIMIZADA PARA MÓVIL) ---
st.set_page_config(
    page_title="IkigAI V1.94 - Executive Workstation", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="collapsed" # En móvil, la barra lateral inicia cerrada para ganar espacio
)

# Estilo "Lienzo Zen" (CSS Limpio - Sin cajas de colores)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    
    /* ELIMINACIÓN DE CAJAS DE MENSAJES (Efecto Gemini) */
    [data-testid="stChatMessage"] { 
        background-color: transparent !important; 
        border: none !important; 
        padding: 5px 0 !important;
    }
    
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.6 !important; text-align: justify; }
    
    /* BOTONES EJECUTIVOS */
    .stDownloadButton button, .stButton button { 
        width: 100%; border-radius: 20px; background-color: transparent !important; 
        color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; 
    }
    
    /* CHAT INPUT MINIMALISTA */
    .stChatInputContainer { padding: 10px 0 !important; background-color: transparent !important; }
    .stChatInput textarea { 
        background-color: #1E1F20 !important; border-radius: 28px !important; 
        border: 1px solid #3C4043 !important; color: #FFFFFF !important; 
    }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Investigador Científico": "Metodología, rigor clínico y APA 7.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital.",
    "Vicedecano Académico": "Gestión académica y normativa.",
    "Director de UCI": "Rigor en datos y seguridad del paciente.",
    "Consultor Salud Digital": "Estrategia territorial y BID.",
    "Estratega de Trading": "Gestión de riesgo y abundancia."
}

# --- 2. FUNCIONES DE LECTURA (ROBUSTAS) ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])

# --- 3. MOTOR DE EXPORTACIÓN (V1.94 - AUTORÍA JAIRO PÉREZ) ---
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def extraer_titulo_dictado(messages, indices_seleccionados):
    if not indices_seleccionados: return "MANUAL TÉCNICO"
    # Analizamos solo las primeras 5 líneas para mayor velocidad
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
    
    section = doc.sections[0]
    for m in ['left', 'right', 'top', 'bottom']: setattr(section, f'{m}_margin', Inches(1))
    
    titulo = extraer_titulo_dictado(messages, indices_seleccionados)
    h = doc.add_heading(titulo, 0)
    h.alignment = 1
    for run in h.runs: run.font.color.rgb = RGBColor(0, 32, 96)

    doc.add_paragraph("").add_run()
    autor = doc.add_paragraph()
    run_a = autor.add_run("Jairo Antonio Pérez Cely")
    run_a.bold = True
    autor.alignment = 1
    doc.add_paragraph("Estratega en Salud Digital e Innovación").alignment = 1
    doc.add_paragraph(f"Generado: {date.today()}").alignment = 1
    doc.add_paragraph("_" * 60).alignment = 1
    
    for idx in sorted(indices_seleccionados):
        for line in messages[idx]["content"].split('\n'):
            if any(x in line.upper() for x in ["COMO IKIGAI", "DOCTOR"]): continue
            clean = re.sub(r'\*+', '', line).strip()
            if not clean: continue
            if line.startswith('#'):
                p = doc.add_heading(clean, level=min(line.count('#'), 3))
                p.paragraph_format.keep_with_next = True
            else:
                p = doc.add_paragraph(clean)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_page_break()
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "ANÁLISIS ESTRATÉGICO"
    slide.placeholders[1].text = f"Autor: Jairo Antonio Pérez Cely\n{date.today()}"
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "export_pool" not in st.session_state: st.session_state.export_pool = []

# --- 5. BARRA LATERAL (SIMPLIFICADA PARA MÓVIL) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧬 IKIGAI</h2>", unsafe_allow_html=True)
    rol_activo = st.selectbox("Rol activo:", options=list(ROLES.keys()))
    
    if st.button("🗑️ Reiniciar Sesión"):
        st.session_state.messages = []; st.session_state.export_pool = []; st.rerun()

    if st.session_state.export_pool:
        st.divider()
        word_data = download_word_compilado(st.session_state.export_pool, st.session_state.messages, rol_activo)
        st.download_button("📄 Exportar Word", data=word_data, file_name=f"Manual_{date.today()}.docx")
    
    up = st.file_uploader("Contexto (PDF/Word):", type=['pdf', 'docx'], accept_multiple_files=True)
    if up and st.button("🧠 PROCESAR"):
        raw = ""
        for f in up: raw += get_pdf_text(f) if f.type == "application/pdf" else get_docx_text(f)
        model = genai.GenerativeModel('gemini-2.5-flash')
        res = model.generate_content(f"Resume puntos clave para un manual: {raw[:40000]}")
        st.session_state.biblioteca[rol_activo] = res.text
        st.success("Contexto integrado.")

# --- 6. WORKSTATION (FLUJO TIPO LIENZO) ---
for i, msg in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            is_sel = i in st.session_state.export_pool
            if st.checkbox(f"📥 Incluir en exportación", key=f"sel_{i}", value=is_sel):
                if i not in st.session_state.export_pool: st.session_state.export_pool.append(i)
            else:
                if i in st.session_state.export_pool: st.session_state.export_pool.remove(i)

if pr := st.chat_input("¿Qué sección diseñamos ahora, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            sys = f"Rol: {rol_activo}. Estilo clínico/ejecutivo. APA 7. Autor: Jairo Pérez Cely."
            lib = st.session_state.biblioteca.get(rol_activo, '')[:30000]
            resp = model.generate_content([sys, f"Contexto: {lib}", pr])
            st.session_state.messages.append({"role": "assistant", "content": resp.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error de conexión: {e}")
