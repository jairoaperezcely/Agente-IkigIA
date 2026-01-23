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
import streamlit.components.v1 as components
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.25 - Executive Hub", page_icon="🧬", layout="wide")

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
    "Professor Universitario": "Pedagogía disruptiva y mentoría médica.",
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

# --- 3. FUNCIONES DE EXPORTACIÓN ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Entregable IkigAI: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()}").bold = True
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Estrategia {role}"
    slide.placeholders[1].text = f"Generado por IkigAI\n{date.today()}"
    # Divide el contenido en puntos para slides
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    for i, p in enumerate(points[:8]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje Estratégico {i+1}"
        slide.placeholders[1].text = p
    bio = BytesIO()
    prs.save(bio)
    return bio.getvalue()

def render_infographic(mermaid_code):
    clean_code = re.sub(r'```mermaid|```', '', mermaid_code).strip()
    components.html(f"""
        <div id="graph-container" style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            <button onclick="window.print()" style="margin-bottom: 15px; padding: 10px 20px; background: #2E86C1; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                📥 Exportar Infografía (Guardar PDF/Imagen)
            </button>
            <div class="mermaid">{clean_code}</div>
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>
        <style> @media print {{ button {{ display: none; }} #graph-container {{ border: none; }} }} </style>
    """, height=700, scrolling=True)

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL (Fuentes y Roles) ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    
    st.divider()
    st.subheader(f"🔌 Fuentes para {rol_activo}")
    t1, t2, t3 = st.tabs(["📄 Archivos", "🔗 Links", "🖼️ Imágenes"])
    
    with t1:
        up = st.file_uploader("Leer PDF, Word, Excel:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
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
            st.session_state.temp_image = Image.open(img_f)
            st.image(st.session_state.temp_image, caption="Imagen cargada")

    st.divider()
    if st.session_state.last_analysis:
        st.subheader("💾 Exportar")
        st.download_button("📄 Word", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 PowerPoint", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("¿Qué entregable diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)

    with st.chat_message("assistant"):
        # MODELO FLASH 2.5 (Configurado como 2.5-flash por estabilidad de API)
        model = genai.GenerativeModel('gemini-2.5-flash') 
        sys = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, ejecutivo, sin clichés. Si pides infografía, responde ÚNICAMENTE con el código Mermaid."
        
        inputs = [sys, f"Contexto leído: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        
        if "graph" in res.text or "sequenceDiagram" in res.text or "mindmap" in res.text:
            render_infographic(res.text)
        else:
            st.markdown(res.text)
            
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.session_state.temp_image = None
        st.rerun() # Asegura que los botones de exportación se actualicen
