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
# 🏛️ CONFIGURACIÓN DE IDENTIDAD INSTITUCIONAL
# ==========================================
st.set_page_config(page_title="Agente IkigAI - Vicedecanatura", page_icon="🏛️", layout="wide")

# CSS para una UI de Nivel Directivo y Móvil
st.markdown("""
    <style>
    /* Estilo de Tablas UNAL */
    .stTable { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }
    th { background-color: #003366 !important; color: white !important; font-weight: bold; text-align: center; text-transform: uppercase; font-size: 13px; }
    td { font-size: 14px; }

    /* Barra Lateral Premium */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #f0f2f6 0%, #ffffff 100%); border-right: 1px solid #d1d5db; }
    [data-testid="stSidebar"] .stMarkdown p { color: #003366; font-weight: 600; font-size: 15px; }
    
    /* Botones y Contenedores */
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; border: 1px solid #003366; transition: 0.3s; height: 45px; }
    .stButton>button:hover { background-color: #003366; color: white; box-shadow: 0 4px 8px rgba(0,51,102,0.3); }
    div[data-testid="stExpander"] { border: 1px solid #003366; border-radius: 12px; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA (DIRECTIVA)
# ==========================================
MEMORIA_MAESTRA = """
PERFIL DEL USUARIO (QUIÉN SOY):
- Líder Transformador en Salud: Médico Especialista en Anestesiología y Cuidado Crítico (UCI), Epidemiólogo Clínico y Doctorando en Bioética.
- Roles de Alto Impacto: Vicedecano Académico de Medicina (UNAL), Director de UCI y Líder de Humanización (HUN), Coordinador de Telemedicina e IA.

INSTRUCCIONES OPERATIVAS:
1. Eres su Secretaría Técnica de Alto Nivel. Tus entregables deben ser IMPECABLES.
2. Formato: Presenta datos e indicadores SIEMPRE en tablas Markdown profesionales.
3. Tono: Formal, institucional, riguroso, equilibrando tecnología con humanismo y bioética.
"""

# ==========================================
# 📖 MOTOR DE LECTURA (SIN ALTERACIONES)
# ==========================================
@st.cache_data
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file); return "".join([p.extract_text() or "" for p in reader.pages])

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
    except: return "No disponible"

# ==========================================
# 🏭 MOTOR DE PRODUCCIÓN (RESTAURACIÓN TOTAL)
# ==========================================
def create_clean_docx(text_content):
    doc = docx.Document()
    # Estilos Vicedecanatura
    for _ in range(4): doc.add_paragraph("")
    t = doc.add_paragraph("INFORME TÉCNICO ESTRATÉGICO"); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.runs[0]; run.bold = True; run.font.size = Pt(24); run.font.color.rgb = RGBColor(0, 51, 102)
    doc.add_paragraph(f"Vicedecanatura Académica / Dirección UCI\nFecha: {date.today()}").alignment = WD_ALIGN_PARAGRAPH.CENTER
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
        if slide.shapes.title: 
            slide.shapes.title.text = info.get("title", "Resumen")
            slide.shapes.title.text_frame.paragraphs[0].font.color.rgb = PtxRGB(0, 51, 102)
        tf = slide.placeholders[1].text_frame
        for p in info.get("content", []):
            para = tf.add_paragraph(); para.text = str(p); para.level = 0
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0); return buffer

# ==========================================
# 💾 GESTIÓN DE ESTADO
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""

# ==========================================
# 🖥️ BARRA LATERAL (8 ROLES + DISEÑO UX)
# ==========================================
with st.sidebar:
    st.image("https://medicina.unal.edu.co/fileadmin/templates/fm/img/logo-facultad-medicina.png", width=220)
    st.markdown("### 🏛️ IkigAI Control Panel")
    st.divider()

    # 1. AUTENTICACIÓN
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]; st.success("🔐 Acceso Verificado")
    else: api_key = st.text_input("🔑 API Key:", type="password")

    # 2. PERFIL ACTIVO (8 ROLES COMPLETOS)
    rol = st.selectbox("👤 Perfil Estratégico:", [
        "Socio Estratégico (Innovación)", "Vicedecano Académico", "Director de UCI", 
        "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", 
        "Mentor de Trading", "Asistente Ejecutivo"
    ])

    prompts_roles = {
        "Socio Estratégico (Innovación)": "Consultor Senior. Reta la instrucción, aplica marcos disruptivos y Design Thinking.",
        "Vicedecano Académico": "Tono institucional formal UNAL. Riguroso, normativo y enfocado en gestión académica.",
        "Director de UCI": "Enfoque clínico intensivo. Prioriza seguridad, guías de práctica clínica y eficiencia hospitalaria.",
        "Consultor Telesalud": "Experto en Salud Digital, Ley 1419 y modelos de prestación en territorios.",
        "Profesor Universitario": "Pedagógico, explicativo, enfocado en educación médica de vanguardia.",
        "Investigador Científico": "Rigor metodológico, análisis de evidencia y normas de publicación científica.",
        "Mentor de Trading": "Analista institucional. Enfoque en liquidez de mercado y gestión de riesgo financiero.",
        "Asistente Ejecutivo": "Conciso, eficiente, experto en agendas, actas y seguimiento de tareas."
    }

    st.divider()

    # 3. MÓDULO DE INSUMOS (Expandible)
    with st.expander("📥 INSUMOS Y CONTEXTO", expanded=False):
        docs = st.file_uploader("Subir PDF/Office/Excel", accept_multiple_files=True)
        if docs and st.button("Procesar Archivos", use_container_width=True):
            acc = ""
            for f in docs:
                if f.type == "application/pdf": acc += get_pdf_text(f)
                elif "word" in f.type: acc += get_docx_text(f)
                elif "sheet" in f.type: acc += get_excel_text(f)
            st.session_state.contexto_texto = acc; st.success("Memoria Lista")
        
        st.divider()
        u_yt = st.text_input("YouTube URL:"); w_url = st.text_input("Web URL:")
        if u_yt and st.button("Analizar YouTube", use_container_width=True): st.session_state.contexto_texto += get_youtube_text(u_yt)

    # 4. MÓDULO DE PRODUCCIÓN (Expandible)
    with st.expander("🛠️ HERRAMIENTAS DE PRODUCCIÓN", expanded=False):
        if st.button("📄 Informe Word", use_container_width=True):
            if st.session_state.messages:
                st.session_state.gen_word = create_clean_docx(st.session_state.messages[-1]["content"])
        if st.session_state.get("gen_word"):
            st.download_button("📥 Bajar Word", st.session_state.gen_word, "informe.docx")

        st.divider()
        if st.button("📊 Diapositivas PPTX", use_container_width=True):
            p_prompt = f"Resume estratégicamente en JSON para PPTX: {st.session_state.messages[-1]['content']}. JSON: [{{'title':'T','content':['A']}}]"
            try:
                genai.configure(api_key=api_key)
                res = genai.GenerativeModel(MODELO_USADO).generate_content(p_prompt).text
                clean_json = res[res.find("["):res.rfind("]")+1]
                st.session_state.gen_pptx = generate_pptx_from_data(json.loads(clean_json))
                st.success("PPTX Generado")
            except: st.error("Error en datos")
        if st.session_state.get("gen_pptx"):
            st.download_button("📥 Bajar PPTX", st.session_state.gen_pptx, "pres.pptx")

    # 5. MULTIMEDIA Y VOZ
    st.divider()
    c1, c2 = st.columns(2)
    with c1: modo_voz = st.toggle("🎙️ Voz")
    with c2: 
        if st.button("🗑️ Reset"): st.session_state.clear(); st.rerun()

# ==========================================
# 🚀 ÁREA PRINCIPAL DE TRABAJO
# ==========================================
st.title(f"🤖 Agente V170: {rol}")
if not api_key: st.warning("⚠️ Ingrese su API Key en la barra lateral."); st.stop()

# Mostrar Chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# Lógica de Voz
if modo_voz:
    audio = mic_recorder(start_prompt="🔴 Hablar", stop_prompt="⏹️ Procesar", key='rec')
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
            tf.write(audio['bytes']); tpath = tf.name
        genai.configure(api_key=api_key); mfile = genai.upload_file(path=tpath)
        while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
        res = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA).generate_content([f"Responde como {rol}:", mfile])
        st.session_state.messages.append({"role": "user", "content": "(Audio Dictado)"})
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        tts = gTTS(text=res.text, lang='es'); fp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(fp.name); st.audio(fp.name); os.remove(tpath); st.rerun()

# Entrada de Texto Directivo
if p := st.chat_input("Escriba su requerimiento estratégico..."):
    st.session_state.messages.append({"role": "user", "content": p}); st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        genai.configure(api_key=api_key); model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
        ctx = st.session_state.contexto_texto
        payload = [f"ROL: {rol}\nPERFIL: {prompts_roles[rol]}\nCONTEXTO: {ctx[:80000]}\nCONSULTA: {p}"]
        response = model.generate_content(payload, stream=True)
        full_res = st.write_stream(chunk.text for chunk in response)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
