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
from pptx.enum.text import PP_ALIGN
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.31 - Executive Strategy Hub", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y eliminación de procastinación.",
    "Director Centro Telemedicina": "Innovación y Salud Digital UNAL. Foco en Hospital Virtual.",
    "Vicedecano Académico": "Gestión y normativa Facultad de Medicina UNAL.",
    "Director de UCI": "Rigor clínico y datos en el HUN.",
    "Investigador Científico": "Metodología y redacción científica.",
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Profesor Universitario": "Pedagogía y mentoría médica.",
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

# --- 3. MOTOR PPTX EVOLUCIONADO ---
def create_strategic_pptx(title, text_content, role):
    prs = Presentation()
    
    # SLIDE 1: PORTADA EJECUTIVA
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title_shape = slide.shapes.title
    subtitle_shape = slide.placeholders[1]
    
    title_shape.text = title.upper()
    subtitle_shape.text = f"Estrategia Integral: {role}\nFecha: {date.today()}\nIkigAI Intelligence System"
    
    # PROCESAMIENTO DE CONTENIDO
    # Dividimos por bloques de párrafos para crear láminas con sentido
    sections = [s.strip() for s in text_content.split('\n\n') if len(s.strip()) > 20]
    
    for i, section in enumerate(sections[:12]): # Límite de 12 láminas
        slide_layout = prs.slide_layouts[1] # Layout Título + Cuerpo
        slide = prs.slides.add_slide(slide_layout)
        
        # Título de la lámina (extraemos la primera línea o frase corta)
        lines = section.split('\n')
        slide.shapes.title.text = lines[0][:50] if lines else f"Eje Estratégico {i+1}"
        
        # Cuerpo de la lámina
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.word_wrap = True
        
        content_lines = lines[1:] if len(lines) > 1 else lines
        for line in content_lines:
            p = tf.add_paragraph()
            p.text = line.strip()
            p.level = 0
            p.space_after = Pt(10)

    bio = BytesIO()
    prs.save(bio)
    return bio.getvalue()

def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Entregable IkigAI: {role}', 0)
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Perfil Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    st.divider()
    t1, t2, t3 = st.tabs(["📄 Documentos", "🔗 Enlaces", "🖼️ Imágenes"])
    with t1:
        up = st.file_uploader("Subir archivos:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer Datos"):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "officedocument.word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "spreadsheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Fuentes integradas.")
    with t2:
        uw, uy = st.text_input("URL Web:"), st.text_input("URL YouTube:")
        if st.button("🌐 Conectar"):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Conexión exitosa.")
    with t3:
        img_f = st.file_uploader("Leer imagen:", type=['jpg', 'jpeg', 'png'])
        if img_f:
            st.session_state.temp_image = Image.open(img_f); st.image(st.session_state.temp_image)

    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 Exportar Entregable")
        st.download_button("📄 Word", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 PowerPoint Pro", data=create_strategic_pptx("Plan Estratégico", st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_PPTX_{rol_activo}.pptx")

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("Escriba la instrucción para su presentación..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, directo, ejecutivo. Sin clichés. Si el usuario pide una presentación, estructura tu respuesta con Títulos claros y puntos clave breves para cada slide."
        inputs = [sys, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.rerun()
