import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os
from io import BytesIO
import json
from datetime import date
import re

# --- LIBRERÍAS DE OFICINA Y GRÁFICOS ---
from pptx import Presentation
from pptx.util import Pt as PtxPt, Inches as PtxInches
from pptx.dml.color import RGBColor as PtxRGB
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
import matplotlib.pyplot as plt
import pandas as pd
import streamlit.components.v1 as components
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- LIBRERÍAS DE VOZ ---
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# ==========================================
# ⚙️ CONFIGURACIÓN DEL SISTEMA
# ==========================================
st.set_page_config(page_title="Agente IkigAI V120", page_icon="🏛️", layout="wide")

# Estilo para Tablas Ejecutivas (Sin afectar el fondo general)
st.markdown("""
    <style>
    .stTable { border-radius: 10px; overflow: hidden; }
    th { background-color: #003366 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
PERFIL DEL USUARIO: Líder en Salud, Vicedecano Académico UNAL, Director UCI HUN, Bioético.
MISIÓN: Secretaría Técnica de Alto Nivel. Entregables impecables.
TABLAS: Usa tablas Markdown profesionales con rigor de datos.
"""

# ==========================================
# 📖 MOTOR DE LECTURA (COMPLETO)
# ==========================================
@st.cache_data
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file); text = ""
    for page in reader.pages: text += page.extract_text() or ""
    return text

@st.cache_data
def get_docx_text(docx_file):
    doc = docx.Document(docx_file); return "\n".join([p.text for p in doc.paragraphs])

@st.cache_data
def get_excel_text(excel_file):
    try:
        sheets = pd.read_excel(excel_file, sheet_name=None); text = ""
        for name, df in sheets.items(): text += f"\n--- HOJA: {name} ---\n{df.to_string()}\n"
        return text
    except: return "Error Excel"

def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "TRANSCRIPCIÓN YT: " + " ".join([i['text'] for i in t])
    except: return "Error YT"

# ==========================================
# 🏭 MOTOR DE PRODUCCIÓN (OFFICE)
# ==========================================
def create_clean_docx(text_content):
    doc = docx.Document()
    t = doc.add_paragraph("INFORME ESTRATÉGICO"); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.runs[0]; run.bold = True; run.font.size = Pt(22); run.font.color.rgb = RGBColor(0, 51, 102)
    doc.add_page_break()
    table_buffer = []; in_table = False
    for line in text_content.split('\n'):
        if "|" in line:
            if "---" in line: in_table = True; continue
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells: table_buffer.append(cells)
        else:
            if in_table and table_buffer:
                table = doc.add_table(rows=len(table_buffer), cols=len(table_buffer[0])); table.style = 'Table Grid'
                for i, row in enumerate(table_buffer):
                    for j, val in enumerate(row):
                        if j < len(table.columns):
                            cell = table.cell(i, j); cell.text = val.replace("**", "")
                            if i == 0:
                                shading = parse_xml(r'<w:shd {} w:fill="003366"/>'.format(nsdecls('w')))
                                cell._tc.get_or_add_tcPr().append(shading)
                                cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
                doc.add_paragraph(""); table_buffer = []; in_table = False
            doc.add_paragraph(line.replace("**", ""))
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0); return buffer

# ==========================================
# 🖥️ BARRA LATERAL (RESTABLECIDA)
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Escudo_de_la_Universidad_Nacional_de_Colombia.svg/1200px-Escudo_de_la_Universidad_Nacional_de_Colombia.svg.png", width=100)
    st.title("IkigAI Master V120")
    st.divider()

    # 1. AUTENTICACIÓN AUTOMÁTICA O MANUAL
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("🔐 Autenticación Automática")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    # RESTAURACIÓN DE LOS 8 ROLES
    rol = st.selectbox("👤 Perfil:", [
        "Socio Estratégico (Innovación)", "Vicedecano Académico", "Director de UCI", 
        "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", 
        "Mentor de Trading", "Asistente Ejecutivo"
    ])

    prompts_roles = {
        "Socio Estratégico (Innovación)": "Consultor Senior. Estrategia disruptiva.",
        "Vicedecano Académico": "Tono institucional UNAL, formal y riguroso.",
        "Director de UCI": "Enfoque clínico UCI y seguridad.",
        "Consultor Telesalud": "Experto en Ley 1419 y Salud Digital.",
        "Profesor Universitario": "Pedagógico y académico.",
        "Investigador Científico": "Rigor científico y normas APA.",
        "Mentor de Trading": "Análisis institucional y liquidez.",
        "Asistente Ejecutivo": "Conciso y enfocado en actas."
    }

    st.divider()

    # 2. MÓDULO INSUMOS
    with st.expander("📥 INGESTAR DATOS", expanded=False):
        docs = st.file_uploader("Subir PDF/Word/Excel", accept_multiple_files=True)
        if docs and st.button("Cargar Memoria"):
            acc = ""
            for f in docs:
                if f.type == "application/pdf": acc += get_pdf_text(f)
                elif "word" in f.type: acc += get_docx_text(f)
                elif "sheet" in f.type: acc += get_excel_text(f)
            st.session_state.contexto_texto = acc; st.success("Listo")
        
        u_yt = st.text_input("URL YouTube:")
        if u_yt and st.button("Leer YT"):
            st.session_state.contexto_texto += get_youtube_text(u_yt)

    # 3. MÓDULO PRODUCCIÓN
    with st.expander("🛠️ HERRAMIENTAS", expanded=False):
        if st.button("📄 Informe Word"):
            if st.session_state.get("messages"):
                st.session_state.gen_word = create_clean_docx(st.session_state.messages[-1]["content"])
        if st.session_state.get("gen_word"):
            st.download_button("📥 Descargar Word", st.session_state.gen_word, "informe.docx")

    # 4. MULTIMEDIA
    with st.expander("🎙️ MULTIMEDIA", expanded=False):
        up_media = st.file_uploader("Audio/Video", type=['mp3','mp4','png','jpg'])
        if up_media and st.button("Subir a Gemini"):
            genai.configure(api_key=api_key)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                tf.write(up_media.read()); tpath = tf.name
            mfile = genai.upload_file(path=tpath)
            while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
            st.session_state.archivo_multimodal = mfile; st.success("Media Procesado")

    st.divider()
    c1, c2 = st.columns(2)
    with c1: modo_voz = st.toggle("Voz")
    with c2: 
        if st.button("Reset"):
            st.session_state.clear(); st.rerun()

# ==========================================
# 🚀 ÁREA PRINCIPAL
# ==========================================
st.title(f"🤖 Agente V120: {rol}")
if not api_key: st.warning("⚠️ Falta Clave API"); st.stop()

if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if modo_voz:
    audio = mic_recorder(start_prompt="🔴", stop_prompt="⏹️", key='rec')
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
            tf.write(audio['bytes']); tpath = tf.name
        genai.configure(api_key=api_key); mfile = genai.upload_file(path=tpath)
        while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
        res = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA).generate_content([f"Rol: {rol}", mfile])
        st.session_state.messages.append({"role": "user", "content": "(Voz)"}); st.session_state.messages.append({"role": "assistant", "content": res.text})
        tts = gTTS(text=res.text, lang='es'); fp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(fp.name); st.audio(fp.name); os.remove(tpath); st.rerun()

if p := st.chat_input("Instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": p}); st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        genai.configure(api_key=api_key); model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
        ctx = st.session_state.contexto_texto
        payload = [f"ROL: {rol}\nDEFINICIÓN: {prompts_roles[rol]}\nCONTEXTO: {ctx[:80000]}\nCONSULTA: {p}"]
        if st.session_state.get("archivo_multimodal"): payload.insert(0, st.session_state.archivo_multimodal)
        response = model.generate_content(payload, stream=True)
        full_res = st.write_stream(chunk.text for chunk in response)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
