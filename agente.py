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
st.set_page_config(page_title="IkigAI V1.27 - Centro Estratégico", page_icon="🧬", layout="wide")

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
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Profesor Universitario": "Pedagogía y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado."
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
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Estrategia {role}"
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    for i, p in enumerate(points[:8]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Punto Estratégico {i+1}"
        slide.placeholders[1].text = p
    bio = BytesIO()
    prs.save(bio)
    return bio.getvalue()

def render_and_export_infographic(mermaid_code):
    clean_code = re.sub(r'```mermaid|```', '', mermaid_code).strip()
    # Generar link para el editor oficial (Base64 no es necesario, URL Encode funciona)
    encoded_mermaid = urllib.parse.quote(clean_code)
    mermaid_url = f"https://mermaid.live/edit#code:{encoded_mermaid}"
    
    st.info("💡 Infografía generada. Use el botón de abajo para descargarla en alta calidad (PNG/PDF/SVG).")
    st.markdown(f'''<a href="{mermaid_url}" target="_blank" style="text-decoration:none;">
        <button style="width:100%; padding:15px; background-color:#2E86C1; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold; font-size:16px;">
            🚀 ABRIR Y DESCARGAR INFOGRAFÍA (Alta Resolución)
        </button>
    </a>''', unsafe_allow_html=True)
    
    components.html(f"""
        <div class="mermaid" style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            {clean_code}
        </div>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>
    """, height=500, scrolling=True)

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Perfil Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    
    st.divider()
    t1, t2, t3 = st.tabs(["📄 Documentos", "🔗 Enlaces", "🖼️ Imágenes"])
    with t1:
        up = st.file_uploader("Subir archivos:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer Datos"):
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

    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 Exportar Texto")
        st.download_button("📄 Descargar Word", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 Descargar PPTX", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if pr := st.chat_input("Instrucción estratégica..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)

    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, ejecutivo, directo. Si pides infografía, responde SOLO con código Mermaid."
        inputs = [sys, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        
        if any(kw in res.text for kw in ["graph", "sequenceDiagram", "mindmap"]):
            render_and_export_infographic(res.text)
        else:
            st.markdown(res.text)
        
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.session_state.temp_image = None
        st.rerun()
