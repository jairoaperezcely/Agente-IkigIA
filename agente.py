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
import re
import urllib.parse

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.30 - Hub de Liderazgo", page_icon="🧬", layout="wide")

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
    "Investigador Científico": "Metodología y redacción científica.",
    "Consultor Salud Digital": "Estratega para BID/MinSalud y territorio.",
    "Profesor Universitario": "Pedagogía y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado."
}

# --- 2. FUNCIONES DE LECTURA (Manteniendo estabilidad) ---
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

# --- 3. FUNCIONES DE EXPORTACIÓN (WORD, PPTX) ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Entregable IkigAI: {role}', 0)
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Estrategia {role}"
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    for i, p in enumerate(points[:8]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje Estratégico {i+1}"; slide.placeholders[1].text = p
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. MOTOR DE INFOGRAFÍA MEJORADO (V3.0) ---
def clean_mermaid_code(text):
    # Elimina bloques de código y texto extra para dejar solo el diagrama
    code = re.sub(r'```mermaid|```', '', text)
    match = re.search(r'(graph|sequenceDiagram|mindmap|gantt|classDiagram|pie)[\s\S]+', code)
    return match.group(0).strip() if match else None

def render_visual_output(text):
    mermaid_code = clean_mermaid_code(text)
    if mermaid_code:
        # Generación de imagen PNG vía Mermaid.ink (Garantizado)
        encoded_mermaid = urllib.parse.quote(mermaid_code)
        image_url = f"https://mermaid.ink/img/{encoded_mermaid}"
        
        st.subheader("📊 Infografía Estratégica")
        
        # Botón de Descarga y Previsualización de Imagen Real
        st.markdown(f'''
            <div style="background-color: white; padding: 20px; border-radius: 15px; border: 1px solid #d1d8e0; text-align: center;">
                <img src="{image_url}" style="max-width: 100%; height: auto; margin-bottom: 15px;">
                <br>
                <a href="{image_url}" target="_blank">
                    <button style="width: 100%; padding: 12px; background-color: #1A5276; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px;">
                        📥 GUARDAR INFOGRAFÍA COMO IMAGEN (PNG)
                    </button>
                </a>
            </div>
        ''', unsafe_allow_html=True)
        return True
    return False

# --- 5. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 6. BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Perfil:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    st.divider()
    t1, t2, t3 = st.tabs(["📄 Documentos", "🔗 Enlaces", "🖼️ Imágenes"])
    with t1:
        up = st.file_uploader("Subir archivos:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer"):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "officedocument.word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "spreadsheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Fuentes integradas.")
    with t2:
        uw, uy = st.text_input("URL Web:"), st.text_input("URL YouTube:")
        if st.button("🌐 Leer Links"):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Conexión exitosa.")
    with t3:
        img_f = st.file_uploader("Leer imagen:", type=['jpg', 'jpeg', 'png'])
        if img_f:
            st.session_state.temp_image = Image.open(img_f); st.image(st.session_state.temp_image)

    if st.session_state.last_analysis:
        st.divider()
        st.download_button("📄 Word", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 PPTX", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

# --- 7. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("Instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        sys = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, ejecutivo. Si pides infografía, responde SOLO con el código Mermaid."
        inputs = [sys, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        if not render_visual_output(res.text): st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.rerun()
