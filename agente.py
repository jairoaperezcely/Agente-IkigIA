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
import streamlit.components.v1 as components
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.16 - Executive Design Center", page_icon="🧬", layout="wide")

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
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    return "".join([page.extract_text() for page in reader.pages])

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def get_excel_text(xlsx_file):
    df = pd.read_excel(xlsx_file)
    return f"CONTENIDO EXCEL:\n{df.to_string()}"

def get_web_text(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        return f"CONTENIDO WEB ({url}):\n" + "\n".join([p.get_text() for p in soup.find_all('p')])
    except: return "Error al leer la web."

def get_yt_text(url):
    try:
        video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        return f"TRANSCRIPCIÓN YOUTUBE:\n" + " ".join([t['text'] for t in transcript])
    except: return "No se encontró transcripción."

# --- 3. FUNCIONES DE DISEÑO EJECUTIVO ---
def create_word_doc(title, content):
    doc = docx.Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Generado por IkigAI - {date.today()} | Rol: {st.session_state.rol_actual}")
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

def create_pptx(title, text_content):
    prs = Presentation()
    # Slide de Título
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = f"Análisis Estratégico IkigAI\n{date.today()}\n{st.session_state.rol_actual}"
    
    # Intento de fragmentar el texto en diapositivas
    paragraphs = text_content.split('\n\n')
    for i, p in enumerate(paragraphs[:10]): # Límite de 10 slides
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Punto Clave {i+1}"
        slide.placeholders[1].text = p
    
    buf = BytesIO(); prs.save(buf); buf.seek(0)
    return buf

def render_infographic(mermaid_code):
    clean_code = re.sub(r'```mermaid|```', '', mermaid_code).strip()
    components.html(f"""
        <div class="mermaid" style="background: white; padding: 20px;">
            {clean_code}
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>""", height=600, scrolling=True)

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
        if st.button("🧠 Leer Documentos"):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif f.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document": st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif f.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Lectura completada.")

    with t2:
        uw, uy = st.text_input("URL Web:"), st.text_input("URL YouTube:")
        if st.button("🌐 Leer Links"):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Fuentes online leídas.")

    with t3:
        img_f = st.file_uploader("Leer imagen:", type=['jpg', 'jpeg', 'png'])
        if img_f:
            st.session_state.temp_image = Image.open(img_f)
            st.image(st.session_state.temp_image, caption="Imagen cargada", use_container_width=True)

    st.divider()
    st.subheader("💾 Exportar Entregables")
    if st.session_state.last_analysis:
        st.download_button("📄 Word", data=create_word_doc("Informe IkigAI", st.session_state.last_analysis), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 PowerPoint", data=create_pptx(f"Estrategia {rol_activo}", st.session_state.last_analysis), file_name=f"IkigAI_{rol_activo}.pptx")

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

with st.expander("🚀 ROI Cognitivo"):
    tareas = st.text_area("Objetivos de hoy:")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("¿Qué diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)

    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo: Ejecutivo, elegante, sin clichés. Si se pide una infografía o diagrama, responde ÚNICAMENTE con el código Mermaid."
        
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

