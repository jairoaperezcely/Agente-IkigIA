import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os
from io import BytesIO
import json
from datetime import date

# --- LIBRERÍAS DE OFICINA Y GRÁFICOS ---
from pptx import Presentation
import matplotlib.pyplot as plt
import pandas as pd
import streamlit.components.v1 as components 

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
st.set_page_config(page_title="Agente V15.6 (Alta Visibilidad)", page_icon="👁️", layout="wide")

MODELO_USADO = 'gemini-2.5-flash' 
# Si falla, cambie por: 'gemini-2.0-flash-exp'

# ==========================================
# FUNCIÓN VISUALIZADORA (FONDO BLANCO FORZADO)
# ==========================================
def plot_mermaid(code):
    """
    Renderiza diagramas Mermaid sobre un fondo BLANCO explícito.
    Esto soluciona el problema de que se vea negro sobre negro.
    """
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ 
                startOnLoad: true, 
                theme: 'default',  
                securityLevel: 'loose',
            }});
        </script>
        <style>
            /* Forzamos el fondo blanco para que sea como una hoja de papel */
            body {{ background-color: white; margin: 0; padding: 20px; }}
            .mermaid {{ display: flex; justify-content: center; }}
        </style>
    </head>
    <body>
        <div class="mermaid">
            {code}
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=600, scrolling=True)

# ==========================================
# FUNCIONES DE LECTURA (INPUT)
# ==========================================

def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def get_excel_text(excel_file):
    try:
        all_sheets = pd.read_excel(excel_file, sheet_name=None)
        text = ""
        for sheet_name, df in all_sheets.items():
            text += f"\n--- HOJA: {sheet_name} ---\n"
            text += df.to_string()
        return text
    except Exception as e: return f"Error Excel: {e}"

def get_pptx_text(pptx_file):
    try:
        prs = Presentation(pptx_file)
        text = ""
        for i, slide in enumerate(prs.slides):
            text += f"\n--- SLIDE {i+1} ---\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"): text += shape.text + "\n"
        return text
    except Exception as e: return f"Error PPTX: {e}"

# ==========================================
# FUNCIONES DE GENERACIÓN (OUTPUT)
# ==========================================

# 1. WORD ACTA
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading(f'Acta: {date.today().strftime("%d/%m/%Y")}', 0)
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "IA"
        doc.add_heading(role, level=2)
        doc.add_paragraph(msg["content"])
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 2. WORD LIMPIO
def create_clean_docx(text_content):
    doc = docx.Document()
    clean_text = text_content.replace("```markdown", "").replace("```", "")
    for paragraph in clean_text.split('\n'):
        if paragraph.strip(): doc.add_paragraph(paragraph)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 3. PPTX
def generate_pptx_from_data(slide_data):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = slide_data[0].get("title", "Presentación IA")
    slide.placeholders[1].text = f"Fecha: {date.today()}"
    for info in slide_data[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = info.get("title", "Título")
        tf = slide.placeholders[1].text_frame
        for point in info.get("content", []):
            p = tf.add_paragraph(); p.text = point; p.level = 0
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

# 4. EXCEL
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, index=False, sheet_name=sheet_name[:30])
    output.seek(0)
    return output

# 5. GRÁFICO MATPLOTLIB
def generate_advanced_chart(chart_data):
    fig, ax = plt.subplots(figsize=(10, 5))
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = chart_data.get("labels", [])
    for ds in chart_data.get("datasets", []):
        if len(ds["values"]) == len(labels):
            if ds.get("type") == "line": ax.plot(labels, ds["values"], label=ds["label"], marker='o')
            else: ax.bar(labels, ds["values"], label=ds["label"], alpha=0.6)
    ax.legend(); ax.set_title(chart_data.get("title", "Gráfico")); plt.tight_layout()
    return fig

# FUNCIONES WEB/YT
def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "YT: " + " ".join([i['text'] for i in t])
    except: return "Error YT"

def get_web_text(url):
    try: return "WEB: " + "\n".join([p.get_text() for p in BeautifulSoup(requests.get(url).content, 'html.parser').find_all('p')])
    except: return "Error Web"

# ==========================================
# ESTADO
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
if "info_archivos" not in st.session_state: st.session_state.info_archivos = "Ninguno"
# Outputs
if "generated_pptx" not in st.session_state: st.session_state.generated_pptx = None
if "generated_chart" not in st.session_state: st.session_state.generated_chart = None
if "generated_excel" not in st.session_state: st.session_state.generated_excel = None
if "generated_word_clean" not in st.session_state: st.session_state.generated_word_clean = None
if "generated_mermaid" not in st.session_state: st.session_state.generated_mermaid = None

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2)
    st.divider()
    rol = st.radio("Rol:", ["Vicedecano Académico", "Director de UCI", "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", "Mentor de Trading", "Asistente Personal"])
    
    prompts_roles = {
        "Vicedecano Académico": "Eres Vicedecano. Riguroso, normativo y formal.",
        "Director de UCI": "Eres Médico Intensivista. Prioriza guías clínicas y seguridad.",
        "Consultor Telesalud": "Eres experto en Salud Digital y Leyes.",
        "Profesor Universitario": "Eres docente. Explica con pedagogía.",
        "Investigador Científico": "Eres metodólogo. Prioriza datos y referencias.",
        "Mentor de Trading": "Eres Trader Institucional. Analiza estructura y liquidez.",
        "Asistente Personal": "Eres asistente ejecutivo eficiente."
    }

    st.subheader("🛠️ GENERADOR")
    
    # 1. WORD
    if st.button("📄 Word (Doc)"):
        if st.session_state.messages:
            st.session_state.generated_word_clean = create_clean_docx(st.session_state.messages[-1]["content"])
            st.success("✅ Doc Listo")
    if st.session_state.generated_word_clean: st.download_button("📥 Bajar Doc", st.session_state.generated_word_clean, "doc.docx")

    # 2. PPTX
    if st.button("🗣️ PPTX"):
        with st.spinner("Creando PPTX..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
            prompt = f"Analiza: {hist}. JSON PPTX: [{{'title':'T','content':['A']}}]"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                st.session_state.generated_pptx = generate_pptx_from_data(json.loads(res.text.replace("```json","").replace("```","").strip()))
                st.success("✅ PPTX Listo")
            except: st.error("Error PPTX")
    if st.session_state.generated_pptx: st.download_button("📥 Bajar PPTX", st.session_state.generated_pptx, "pres.pptx")

    # 3. EXCEL
    if st.button("x ̅  Excel"):
        with st.spinner("Creando Excel..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Analiza: {hist}. JSON Excel: {{'Hoja1': [{{'ColA':'Val1'}}]}}"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO
