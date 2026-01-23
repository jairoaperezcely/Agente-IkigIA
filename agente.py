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
st.set_page_config(page_title="Agente IkigAI V130", page_icon="🏛️", layout="wide")

# Estilo para Tablas Ejecutivas y Contraste de UI
st.markdown("""
    <style>
    .stTable { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    th { background-color: #003366 !important; color: white !important; font-weight: bold; text-align: center; }
    div[data-testid="stExpander"] { border: 1px solid #003366; border-radius: 10px; background-color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA (DIRECTIVA)
# ==========================================
MEMORIA_MAESTRA = """
PERFIL DEL USUARIO: Líder en Salud, Vicedecano Académico UNAL, Director UCI HUN, Epidemiólogo y Doctor en Bioética.
MISIÓN: Eres su Secretaría Técnica de Alto Nivel. Generas entregables (Word, PPTX, Excel) impecables.
TABLAS: Usa SIEMPRE tablas Markdown para presentar indicadores o comparativas.
"""

# ==========================================
# 🎨 MOTOR VISUAL (MERMAID JS)
# ==========================================
def plot_mermaid(code):
    html_code = f"""
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'base' }});
    </script>
    <div class="mermaid" style="display: flex; justify-content: center;">{code}</div>
    """
    components.html(html_code, height=500, scrolling=True)

# ==========================================
# 📖 MOTOR DE LECTURA (INGENIERÍA)
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

@st.cache_data
def get_pptx_text(pptx_file):
    try:
        prs = Presentation(pptx_file); text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"): text += shape.text + "\n"
        return text
    except: return "Error PPTX"

def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "YT: " + " ".join([i['text'] for i in t])
    except: return "No disponible"

def get_web_text(url):
    try: 
        r = requests.get(url, timeout=10); s = BeautifulSoup(r.content, 'html.parser')
        return "WEB: " + "\n".join([p.get_text() for p in s.find_all('p')])
    except: return "Error Web"

# ==========================================
# 🏭 MOTOR DE PRODUCCIÓN (OFFICE PREMIUM)
# ==========================================

# --- 1. GENERADOR WORD ---
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

# --- 2. GENERADOR POWERPOINT (RESTAURADO) ---
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
# 💾 GESTIÓN DE ESTADO
# ==========================================
keys = ["messages", "contexto_texto", "archivo_multimodal", "gen_word", "gen_pptx", "gen_mermaid"]
for k in keys:
    if k not in st.session_state: st.session_state[k] = [] if k == "messages" else "" if k == "contexto_texto" else None

# ==========================================
# 🖥️ BARRA LATERAL (EJECUTIVA + 8 ROLES)
# ==========================================
with st.sidebar:
    st.image("https://medicina.unal.edu.co/fileadmin/templates/fm/img/logo-facultad-medicina.png", width=220)
    st.markdown("### 🏛️ IkigAI Dashboard V130")
    st.divider()

    # Autenticación Automática
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]; st.success("🔐 Acceso Verificado")
    else: api_key = st.text_input("🔑 API Key:", type="password")

    # Restauración de los 8 Roles
    rol = st.selectbox("👤 Perfil Activo:", [
        "Socio Estratégico (Innovación)", "Vicedecano Académico", "Director de UCI", 
        "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", 
        "Mentor de Trading", "Asistente Ejecutivo"
    ])

    prompts_roles = {
        "Socio Estratégico (Innovación)": "Consultor Senior. Estrategia disruptiva.",
        "Vicedecano Académico": "Tono institucional UNAL, formal y riguroso.",
        "Director de UCI": "Enfoque clínico UCI y seguridad del paciente.",
        "Consultor Telesalud": "Experto en Ley 1419 y Salud Digital.",
        "Profesor Universitario": "Pedagógico y formación médica.",
        "Investigador Científico": "Rigor científico, evidencia y normas APA.",
        "Mentor de Trading": "Análisis institucional y liquidez.",
        "Asistente Ejecutivo": "Conciso, eficiente y enfocado en actas."
    }

    st.divider()

    # Módulo de Ingesta
    with st.expander("📥 INGESTAR DATOS", expanded=False):
        docs = st.file_uploader("Subir PDF/Word/Excel", accept_multiple_files=True)
        if docs and st.button("Cargar Memoria", use_container_width=True):
            acc = ""
            for f in docs:
                if f.type == "application/pdf": acc += get_pdf_text(f)
                elif "word" in f.type: acc += get_docx_text(f)
                elif "sheet" in f.type: acc += get_excel_text(f)
            st.session_state.contexto_texto = acc; st.success("Documentos Cargados")
        
        st.divider()
        u_yt = st.text_input("YouTube URL:"); w_url = st.text_input("Web URL:")
        if u_yt and st.button("Leer YT"): st.session_state.contexto_texto += get_youtube_text(u_yt)
        if w_url and st.button("Leer Web"): st.session_state.contexto_texto += get_web_text(w_url)

    # Módulo de Producción (PPTX Restaurado)
    with st.expander("🛠️ HERRAMIENTAS", expanded=False):
        if st.button("📄 Informe Word", use_container_width=True):
            if st.session_state.messages:
                st.session_state.gen_word = create_clean_docx(st.session_state.messages[-1]["content"])
        if st.session_state.gen_word:
            st.download_button("📥 Bajar Word", st.session_state.gen_word, "informe.docx")

        st.divider()
        if st.button("📊 Diapositivas PPTX", use_container_width=True):
            p_prompt = f"Analiza estratégicamente y genera JSON para PPTX: {st.session_state.messages[-1]['content']}. JSON: [{{'title':'T','content':['A']}}]. SOLO JSON."
            try:
                genai.configure(api_key=api_key)
                res = genai.GenerativeModel(MODELO_USADO).generate_content(p_prompt).text
                clean_json = res[res.find("["):res.rfind("]")+1]
                st.session_state.gen_pptx = generate_pptx_from_data(json.loads(clean_json))
                st.success("PowerPoint Listo")
            except: st.error("Error en estructura de slides")
        if st.session_state.gen_pptx:
            st.download_button("📥 Bajar PPTX", st.session_state.gen_pptx, "pres.pptx")

    # Módulo Multimedia
    with st.expander("🎙️ MULTIMEDIA", expanded=False):
        up_media = st.file_uploader("Multimedia (Voz/Video)", type=['mp3','mp4','png','jpg'])
        if up_media and st.button("Subir a Gemini Cloud"):
            genai.configure(api_key=api_key)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                tf.write(up_media.read()); tpath = tf.name
            mfile = genai.upload_file(path=tpath)
            while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
            st.session_state.archivo_multimodal = mfile; st.success("Binario listo"); os.remove(tpath)

    st.divider()
    c1, c2 = st.columns(2)
    with c1: modo_voz = st.toggle("🎙️ Voz")
    with c2: 
        if st.button("🗑️ Reset"): st.session_state.clear(); st.rerun()

# ==========================================
# 🚀 ÁREA PRINCIPAL
# ==========================================
st.title(f"🤖 Agente V130: {rol}")
if not api_key: st.warning("⚠️ Ingrese su clave en la barra lateral."); st.stop()

if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if modo_voz:
    audio = mic_recorder(start_prompt="🔴 Hablar", stop_prompt="⏹️ Procesar", key='rec')
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
            tf.write(audio['bytes']); tpath = tf.name
        genai.configure(api_key=api_key); mfile = genai.upload_file(path=tpath)
        while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
        res = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA).generate_content([f"Responde como {rol}:", mfile])
        st.session_state.messages.append({"role": "user", "content": "(Voz)"}); st.session_state.messages.append({"role": "assistant", "content": res.text})
        tts = gTTS(text=res.text, lang='es'); fp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(fp.name); st.audio(fp.name); os.remove(tpath); st.rerun()

if p := st.chat_input("Escriba su requerimiento estratégico..."):
    st.session_state.messages.append({"role": "user", "content": p}); st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        genai.configure(api_key=api_key); model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
        ctx = st.session_state.contexto_texto
        payload = [f"ROL: {rol}\nPERFIL: {prompts_roles[rol]}\nCONTEXTO: {ctx[:80000]}\nCONSULTA: {p}"]
        if st.session_state.get("archivo_multimodal"): payload.insert(0, st.session_state.archivo_multimodal)
        response = model.generate_content(payload, stream=True)
        full_res = st.write_stream(chunk.text for chunk in response)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
