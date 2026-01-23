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
st.set_page_config(page_title="IkigAI V1.32 - Academic & Executive Hub", page_icon="🧬", layout="wide")

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
    "Investigador Científico": "Metodología y redacción científica de alto impacto.",
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Profesor Universitario": "Pedagogía y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado."
}

# --- 2. FUNCIONES DE LECTURA (Permanecen intactas) ---
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

# --- 3. MOTOR DE EXPORTACIÓN CON SOPORTE APA 7 ---
def create_strategic_pptx(title, text_content, role):
    prs = Presentation()
    # PORTADA
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title.upper()
    slide.placeholders[1].text = f"Estrategia Integral: {role}\nReferencia Normativa: APA 7\n{date.today()}"
    
    sections = [s.strip() for s in text_content.split('\n\n') if len(s.strip()) > 20]
    for i, section in enumerate(sections[:12]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        lines = section.split('\n')
        # Detectar si es la sección de referencias para darle un layout distinto si se desea
        slide.shapes.title.text = lines[0][:50] if lines else f"Eje {i+1}"
        tf = slide.placeholders[1].text_frame
        tf.word_wrap = True
        content_lines = lines[1:] if len(lines) > 1 else lines
        for line in content_lines:
            p = tf.add_paragraph()
            p.text = line.strip()
            p.space_after = Pt(8)
            # Sangría francesa simulada para referencias en la última lámina
            if "Referencias" in lines[0] or "Bibliografía" in lines[0]:
                p.font.size = Pt(14)
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Entregable IkigAI: {role}', 0)
    doc.add_paragraph(f"Documento bajo normas APA 7 - {date.today()}").italic = True
    for p in content.split('\n'):
        if p.strip():
            paragraph = doc.add_paragraph(p)
            # Aplicar sangría francesa si detectamos la sección de referencias
            if "Referencias" in p or (len(p) > 50 and "(" in p and ")" in p and "." in p):
                paragraph.paragraph_format.left_indent = Inches(0.5)
                paragraph.paragraph_format.first_line_indent = Inches(-0.5)
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
        st.subheader("💾 Exportar (Normas APA 7)")
        st.download_button("📄 Word (APA)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_APA_{rol_activo}.docx")
        st.download_button("📊 PPTX (APA)", data=create_strategic_pptx("Plan Estratégico", st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_PPTX_APA_{rol_activo}.pptx")

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("Escriba su instrucción (IkigAI aplicará APA 7)..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        # INSTRUCCIÓN MANDATORIA APA 7
        sys = f"""Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. 
        REGLA DE ORO: Todas las citas bibliográficas y la lista de referencias final deben estar estrictamente en formato APA 7ma Edición.
        Estilo clínico, directo, ejecutivo. Sin clichés."""
        
        inputs = [sys, f"Contexto leído: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.rerun()
