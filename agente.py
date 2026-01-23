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

# --- LIBRERÍAS DE OFICINA Y GRÁFICOS AVANZADOS ---
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
# ⚙️ CONFIGURACIÓN DEL SISTEMA Y ESTÉTICA EJECUTIVA
# ==========================================
st.set_page_config(page_title="Agente IkigAI - Secretaría Técnica", page_icon="🏛️", layout="wide")

# Inyección de CSS para Tablas Premium y UI Ejecutiva Optimizada
st.markdown("""
    <style>
    .stTable { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    th { background-color: #003366 !important; color: white !important; font-weight: bold; text-align: center; font-size: 14px; }
    td { font-size: 14px; border-bottom: 1px solid #f0f0f0; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 15px; background-color: #fdfdfd; margin-bottom: 1rem; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; transition: 0.3s; border: 1px solid #003366; }
    .stButton>button:hover { background-color: #003366; color: white; }
    /* Ajuste para dispositivos móviles */
    @media (max-width: 768px) { .main .block-container { padding-top: 1rem; } }
    </style>
    """, unsafe_allow_html=True)

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA (DIRECTIVA)
# ==========================================
MEMORIA_MAESTRA = """
PERFIL: Secretaría Técnica de Alto Nivel para el Vicedecano de Medicina UNAL y Director UCI HUN.
MISIÓN: Generar entregables estratégicos con rigor académico y normativo.
ESTÁNDAR: Tablas Markdown impecables, tono formal-ejecutivo, análisis profundo de documentos.
"""

# ==========================================
# 🎨 MOTORES VISUALES
# ==========================================
def plot_mermaid(code):
    html_code = f"""
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'base', securityLevel: 'loose' }});
    </script>
    <div class="mermaid" style="display: flex; justify-content: center;">{code}</div>
    """
    components.html(html_code, height=500, scrolling=True)

# ==========================================
# 📖 MOTOR DE LECTURA (INGENIERÍA MULTIFORMATO)
# ==========================================
@st.cache_data
def get_pdf_text(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages: text += page.extract_text() or ""
        return text
    except: return "Error crítico: El PDF no pudo ser procesado."

@st.cache_data
def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

@st.cache_data
def get_excel_text(excel_file):
    try:
        sheets = pd.read_excel(excel_file, sheet_name=None)
        text = ""
        for name, df in sheets.items():
            text += f"\n--- HOJA: {name} ---\n{df.to_string()}\n"
        return text
    except: return "Error leyendo archivo Excel."

@st.cache_data
def get_pptx_text(pptx_file):
    try:
        prs = Presentation(pptx_file); text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"): text += shape.text + "\n"
        return text
    except: return "Error leyendo archivo PPTX."

def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "CONTENIDO YT: " + " ".join([i['text'] for i in t])
    except: return "No se pudo obtener transcripción de YouTube."

def get_web_text(url):
    try: 
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}); soup = BeautifulSoup(resp.content, 'html.parser')
        return "CONTENIDO WEB: " + "\n".join([p.get_text() for p in soup.find_all('p')])
    except: return "Error en lectura de página web."

# ==========================================
# 🏭 MOTOR DE PRODUCCIÓN (OFFICE PREMIUM)
# ==========================================

def create_clean_docx(text_content):
    doc = docx.Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    # Portada Ejecutiva UNAL
    for _ in range(4): doc.add_paragraph("")
    t = doc.add_paragraph("INFORME TÉCNICO ESTRATÉGICO"); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.runs[0]; run.bold = True; run.font.size = Pt(24); run.font.color.rgb = RGBColor(0, 51, 102)
    doc.add_paragraph(f"Vicedecanatura Académica / Dirección UCI\nFecha: {date.today()}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    table_buffer = []; in_table = False
    for line in text_content.split('\n'):
        stripped = line.strip()
        if "|" in stripped:
            if "---" in stripped: in_table = True; continue
            cells = [c.strip() for c in stripped.split('|') if c.strip()]
            if cells: table_buffer.append(cells)
        else:
            if in_table and table_buffer:
                # Validación de uniformidad de columnas
                if all(len(row) == len(table_buffer[0]) for row in table_buffer):
                    table = doc.add_table(rows=len(table_buffer), cols=len(table_buffer[0])); table.style = 'Table Grid'
                    for i, row in enumerate(table_buffer):
                        for j, val in enumerate(row):
                            cell = table.cell(i, j); cell.text = val.replace("**", "").strip()
                            if i == 0: # Cabecera Institucional
                                shading = parse_xml(r'<w:shd {} w:fill="003366"/>'.format(nsdecls('w')))
                                cell._tc.get_or_add_tcPr().append(shading)
                                cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
                                cell.paragraphs[0].runs[0].font.bold = True
                doc.add_paragraph(""); table_buffer = []; in_table = False
            
            if stripped.startswith("#"):
                doc.add_heading(stripped.replace("#", "").strip(), level=2).runs[0].font.color.rgb = RGBColor(0, 51, 102)
            elif stripped:
                p = doc.add_paragraph(stripped.replace("**", "")); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0); return buffer

def generate_pptx_from_data(slide_data):
    prs = Presentation()
    for info in slide_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        if slide.shapes.title: 
            slide.shapes.title.text = info.get("title", "Punto Estratégico")
            slide.shapes.title.text_frame.paragraphs[0].font.color.rgb = PtxRGB(0, 51, 102)
        tf = slide.placeholders[1].text_frame
        for point in info.get("content", []):
            p = tf.add_paragraph(); p.text = str(point); p.level = 0
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0); return buffer

# ==========================================
# 💾 GESTIÓN DE ESTADO (PERSISTENCIA)
# ==========================================
keys = ["messages", "contexto_texto", "multimodal_file", "gen_word", "gen_pptx", "gen_mermaid"]
for k in keys:
    if k not in st.session_state: st.session_state[k] = [] if k == "messages" else "" if k == "contexto_texto" else None

# ==========================================
# 🖥️ BARRA LATERAL EJECUTIVA (REDISEÑO UX)
# ==========================================
with st.sidebar:
    st.image("https://medicina.unal.edu.co/fileadmin/templates/fm/img/logo-facultad-medicina.png", width=220)
    st.markdown("### 🏛️ IkigAI Control Panel")
    st.divider()

    # --- MÓDULO 1: IDENTIDAD ---
    with st.container():
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]; st.success("🔐 Conexión Premium Activa")
        else: api_key = st.text_input("🔑 API Key:", type="password")

        rol = st.selectbox("👤 Perfil Activo:", [
            "Vicedecano Académico", "Director UCI", "Socio Estratégico", "Mentor de Trading", "Investigador"
        ])
    
    st.divider()

    # --- MÓDULO 2: INSUMOS (Expandible) ---
    with st.expander("📥 Ingesta de Datos y Contexto", expanded=False):
        uploaded_docs = st.file_uploader("Documentos (PDF/Office)", accept_multiple_files=True)
        if uploaded_docs and st.button("Procesar Archivos", use_container_width=True):
            acc = ""
            for f in uploaded_docs:
                if f.type == "application/pdf": acc += get_pdf_text(f)
                elif "word" in f.type: acc += get_docx_text(f)
                elif "sheet" in f.type: acc += get_excel_text(f)
            st.session_state.contexto_texto += acc
            st.success("Memoria actualizada")
        
        st.divider()
        u_yt = st.text_input("Analizar YouTube:"); w_url = st.text_input("Analizar Web:")
        if u_yt and st.button("Extraer Transcripción"): st.session_state.contexto_texto += get_youtube_text(u_yt)
        if w_url and st.button("Extraer Contenido Web"): st.session_state.contexto_texto += get_web_text(w_url)

    # --- MÓDULO 3: PRODUCCIÓN (Expandible) ---
    with st.expander("🛠️ Centro de Producción", expanded=False):
        if st.button("📄 Generar Word Directivo", use_container_width=True):
            if st.session_state.messages:
                st.session_state.gen_word = create_clean_docx(st.session_state.messages[-1]["content"])
        if st.session_state.gen_word:
            st.download_button("📥 Descargar Reporte (.docx)", st.session_state.gen_word, "informe_ejecutivo.docx")

        st.divider()
        if st.button("📊 Generar Diapositivas PPTX", use_container_width=True):
            p_prompt = f"Resume estratégicamente: {st.session_state.messages[-1]['content']}. JSON: [{{'title':'T','content':['P1','P2']}}]"
            try:
                genai.configure(api_key=api_key)
                res = genai.GenerativeModel(MODELO_USADO).generate_content(p_prompt).text
                clean_json = res[res.find("["):res.rfind("]")+1]
                st.session_state.gen_pptx = generate_pptx_from_data(json.loads(clean_json))
                st.success("PowerPoint Generado")
            except: st.error("Error en estructuración de datos.")
        if st.session_state.gen_pptx:
            st.download_button("📥 Descargar Diapositivas (.pptx)", st.session_state.gen_pptx, "presentacion_directiva.pptx")

    # --- MÓDULO 4: MULTIMEDIA ---
    st.divider()
    up_media = st.file_uploader("Multimedia (Audio/Video)", type=['mp3','mp4','png','jpg'])
    if up_media and st.button("Analizar con Gemini Vision/Voz", use_container_width=True):
        genai.configure(api_key=api_key)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
            tf.write(up_media.read()); tpath = tf.name
        mfile = genai.upload_file(path=tpath)
        while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
        st.session_state.multimodal_file = mfile; st.success("Multimedia lista"); os.remove(tpath)

    st.divider()
    c1, c2 = st.columns(2)
    with c1: modo_voz = st.toggle("🎙️ Voz")
    with c2: 
        if st.button("🗑️ Reset"): st.session_state.clear(); st.rerun()

# ==========================================
# 🚀 ÁREA PRINCIPAL DE TRABAJO (CHAT)
# ==========================================
st.title(f"🤖 Agente Omni-Directivo: {rol}")

# Mostrar Historial
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# Lógica de Voz (Bidireccional)
if modo_voz:
    audio = mic_recorder(start_prompt="🔴 Iniciar Grabación", stop_prompt="⏹️ Detener y Procesar", key='rec')
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
            tf.write(audio['bytes']); tpath = tf.name
        genai.configure(api_key=api_key); mfile = genai.upload_file(path=tpath)
        while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
        res = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA).generate_content([f"Responde como {rol}:", mfile])
        st.session_state.messages.append({"role": "user", "content": "(Mensaje de Voz)"})
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        # Síntesis de voz de la respuesta
        tts = gTTS(text=res.text, lang='es'); fp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(fp.name); st.audio(fp.name); os.remove(tpath); st.rerun()

# Entrada de Texto Directivo
if p := st.chat_input("Escriba su instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": p}); st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        genai.configure(api_key=api_key); model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
        ctx = st.session_state.contexto_texto
        payload = [f"CONTEXTO DOCUMENTAL: {ctx[:80000]}\n\nCONSULTA: {p}"]
        if st.session_state.multimodal_file: payload.insert(0, st.session_state.multimodal_file)
        
        response = model.generate_content(payload, stream=True)
        full_res = st.write_stream(chunk.text for chunk in response)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
