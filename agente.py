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
# ⚙️ CONFIGURACIÓN DEL SISTEMA Y ESTILO FORZADO
# ==========================================
st.set_page_config(page_title="Agente IkigAI V140", page_icon="🏛️", layout="wide")

# CSS BLINDADO: Fuerza el contraste para evitar el error de letra blanca
st.markdown("""
    <style>
    /* Tablas ejecutivas */
    .stTable { border-radius: 10px; overflow: hidden; }
    th { background-color: #003366 !important; color: white !important; font-weight: bold; }
    
    /* FUERZA EL COLOR DE LA BARRA LATERAL (FONDO Y TEXTO) */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6 !important;
    }
    /* Fuerza texto negro en toda la barra lateral */
    [data-testid="stSidebar"] * {
        color: #000000 !important;
    }
    /* Ajuste para que los botones dentro del sidebar sigan siendo legibles */
    [data-testid="stSidebar"] button p {
        color: inherit !important;
    }
    /* Estilo para los expanders */
    .stExpander {
        border: 1px solid #003366 !important;
        background-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
PERFIL: Vicedecano Académico Medicina UNAL, Director UCI HUN, Bioético.
MISIÓN: Secretaría Técnica Digital de Alto Nivel. 
REGLA: Usa tablas Markdown impecables para indicadores.
"""

# ==========================================
# 📖 MOTOR DE LECTURA (INGENIERÍA)
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
        return "YT: " + " ".join([i['text'] for i in t])
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

def generate_pptx_from_data(slide_data):
    prs = Presentation()
    for info in slide_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        if slide.shapes.title: slide.shapes.title.text = info.get("title", "Análisis")
        tf = slide.placeholders[1].text_frame
        for p in info.get("content", []): tf.add_paragraph().text = str(p)
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0); return buffer

# ==========================================
# 🖥️ BARRA LATERAL (8 ROLES + FIX AUTENTICACIÓN)
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Escudo_de_la_Universidad_Nacional_de_Colombia.svg/1200px-Escudo_de_la_Universidad_Nacional_de_Colombia.svg.png", width=100)
    st.markdown("### 🏛️ Dashboard V140")
    st.divider()

    # 1. AUTENTICACIÓN AUTOMÁTICA (RESTABLECIDA)
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]; st.success("🔐 Acceso Automático")
    else:
        api_key = st.text_input("🔑 Ingrese API Key:", type="password")

    # 2. SELECCIÓN DE ROL (8 ROLES RESTAURADOS)
    rol = st.selectbox("👤 Perfil:", [
        "Socio Estratégico (Innovación)", "Vicedecano Académico", "Director de UCI", 
        "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", 
        "Mentor de Trading", "Asistente Ejecutivo"
    ])

    prompts_roles = {
        "Socio Estratégico (Innovación)": "Consultor Senior disruptivo.",
        "Vicedecano Académico": "Tono institucional formal UNAL.",
        "Director de UCI": "Enfoque clínico UCI y seguridad.",
        "Consultor Telesalud": "Experto en Ley 1419 y Salud Digital.",
        "Profesor Universitario": "Pedagógico y académico.",
        "Investigador Científico": "Rigor metodológico APA.",
        "Mentor de Trading": "Análisis institucional y liquidez.",
        "Asistente Ejecutivo": "Eficiente y enfocado en actas."
    }

    st.divider()

    # 3. MÓDULO INSUMOS
    with st.expander("📥 INGESTAR DATOS", expanded=False):
        docs = st.file_uploader("Documentos", accept_multiple_files=True)
        if docs and st.button("Cargar Memoria"):
            acc = ""
            for f in docs:
                if f.type == "application/pdf": acc += get_pdf_text(f)
                elif "word" in f.type: acc += get_docx_text(f)
                elif "sheet" in f.type: acc += get_excel_text(f)
            st.session_state.contexto_texto = acc; st.success("Listo")
        
        u_yt = st.text_input("YouTube:"); w_url = st.text_input("Web URL:")
        if u_yt and st.button("Analizar YT"): st.session_state.contexto_texto += get_youtube_text(u_yt)

    # 4. MÓDULO HERRAMIENTAS (PPTX RESTAURADO)
    with st.expander("🛠️ HERRAMIENTAS", expanded=False):
        if st.button("📄 Generar Word"):
            if st.session_state.get("messages"):
                st.session_state.gen_word = create_clean_docx(st.session_state.messages[-1]["content"])
        if st.session_state.get("gen_word"):
            st.download_button("📥 Descargar Word", st.session_state.gen_word, "informe.docx")

        st.divider()
        if st.button("📊 Generar PPTX"):
            p_prompt = f"Genera JSON para PPTX: {st.session_state.messages[-1]['content']}. JSON: [{{'title':'T','content':['A']}}]"
            try:
                genai.configure(api_key=api_key)
                res = genai.GenerativeModel(MODELO_USADO).generate_content(p_prompt).text
                clean_json = res[res.find("["):res.rfind("]")+1]
                st.session_state.gen_pptx = generate_pptx_from_data(json.loads(clean_json))
                st.success("PPTX Listo")
            except: st.error("Error en datos")
        if st.session_state.get("gen_pptx"):
            st.download_button("📥 Descargar PPTX", st.session_state.gen_pptx, "pres.pptx")

    # 5. MULTIMEDIA
    with st.expander("🎙️ MULTIMEDIA", expanded=False):
        up_media = st.file_uploader("Audio/Video", type=['mp3','mp4','png','jpg'])
        if up_media and st.button("Analizar Multimedia"):
            genai.configure(api_key=api_key)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                tf.write(up_media.read()); tpath = tf.name
            mfile = genai.upload_file(path=tpath)
            while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
            st.session_state.archivo_multimodal = mfile; st.success("Media listo")

    st.divider()
    c1, c2 = st.columns(2)
    with c1: modo_voz = st.toggle("Voz")
    with c2: 
        if st.button("Reset"): st.session_state.clear(); st.rerun()

# ==========================================
# 🚀 ÁREA PRINCIPAL
# ==========================================
st.title(f"🤖 Agente V140: {rol}")
if not api_key: st.warning("⚠️ Ingrese Clave API."); st.stop()

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

if p := st.chat_input("Escriba su instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": p}); st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        genai.configure(api_key=api_key); model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
        ctx = st.session_state.contexto_texto
        payload = [f"ROL: {rol}\nDEFINICIÓN: {prompts_roles[rol]}\nCONTEXTO: {ctx[:80000]}\nCONSULTA: {p}"]
        if st.session_state.get("archivo_multimodal"): payload.insert(0, st.session_state.archivo_multimodal)
        response = model.generate_content(payload, stream=True)
        full_res = st.write_stream(chunk.text for chunk in response)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
