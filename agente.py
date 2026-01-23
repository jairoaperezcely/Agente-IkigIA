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

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.34 - Executive Strategy Hub", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo, sostenibilidad del líder y eliminación de procastinación.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL. Foco en Hospital Virtual.",
    "Vicedecano Académico": "Gestión y normativa Facultad de Medicina UNAL.",
    "Director de UCI": "Rigor clínico, seguridad del paciente y datos en el HUN.",
    "Investigador Científico": "Metodología y redacción científica de alto impacto.",
    "Consultor Salud Digital": "Estrategia BID/MinSalud, territorio e interculturalidad.",
    "Profesor Universitario": "Pedagogía disruptiva y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado (Wyckoff/SMC)."
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

# --- 3. MOTOR DE EXPORTACIÓN OFFICE ELEGANTE ---
def download_word_apa(content, role):
    doc = docx.Document()
    doc.add_heading(f'Informe Estratégico: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()} | Formato APA 7").italic = True
    for p in content.split('\n'):
        if p.strip():
            paragraph = doc.add_paragraph(p)
            if "Referencias" in p or (len(p) > 60 and "(" in p and ")" in p):
                paragraph.paragraph_format.left_indent = Inches(0.5)
                paragraph.paragraph_format.first_line_indent = Inches(-0.5)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx_pro(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"ESTRATEGIA {role.upper()}"
    slide.placeholders[1].text = f"Generado por IkigAI Engine\n{date.today()}\nNormas APA 7"
    points = [p for p in content.split('\n') if len(p.strip()) > 35]
    for i, p in enumerate(points[:10]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje Estratégico {i+1}"
        slide.placeholders[1].text = p[:600]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

def download_excel_pro(content):
    try:
        lines = [l for l in content.split('\n') if "|" in l and "---" not in l]
        if len(lines) < 2: return None
        data = [re.split(r'\s*\|\s*', l.strip('|')) for l in lines]
        df = pd.DataFrame(data[1:], columns=data[0])
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Datos IkigAI', index=False)
            workbook, worksheet = writer.book, writer.sheets['Datos IkigAI']
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
                worksheet.set_column(col_num, col_num, 25)
        return bio.getvalue()
    except: return None

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL (Restaurada con Exportadores) ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    st.divider()
    
    st.subheader(f"🔌 Fuentes para {rol_activo}")
    t1, t2, t3 = st.tabs(["📄 Archivos", "🔗 Links", "🖼️ Imágenes"])
    with t1:
        up = st.file_uploader("Subir:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer"):
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

    # SECCIÓN DE EXPORTACIÓN PERMANENTE SI HAY ANÁLISIS
    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 Exportar Entregables")
        st.download_button("📄 Informe Word (APA 7)", data=download_word_apa(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_Informe_{rol_activo}.docx")
        st.download_button("📊 Presentación PPTX", data=download_pptx_pro(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_Presentacion_{rol_activo}.pptx")
        
        xl_data = download_excel_pro(st.session_state.last_analysis)
        if xl_data:
            st.download_button("📈 Tabla Excel Elegante", data=xl_data, file_name=f"IkigAI_Datos_{rol_activo}.xlsx")

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("Instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys = f"""Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. 
        Estilo clínico, ejecutivo, sin clichés. Citas y referencias en APA 7. 
        Si hay datos comparativos, usa tablas Markdown."""
        
        inputs = [sys, f"Contexto leído: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.rerun()
