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
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD ESTRATÉGICA ---
st.set_page_config(
    page_title="IkigAI V1.69 - Robust Executive Hub", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS V1.69: Interfaz Zen de Alta Densidad
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color: #FFFFFF !important; font-weight: 400; }
    
    /* Contenedores de Chat */
    [data-testid="stChatMessage"] { 
        background-color: #050505 !important; 
        border: 1px solid #1A1A1A !important; 
        border-radius: 10px !important;
        margin-bottom: 10px;
    }
    
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    
    /* Referencias APA 7: Contraste Quirúrgico */
    blockquote { 
        border-left: 4px solid #00E6FF !important; 
        background-color: #0D1117 !important; 
        padding: 15px !important; 
        border-radius: 0 10px 10px 0;
    }
    blockquote p { color: #58A6FF !important; font-style: italic !important; }

    /* Botones de Acción */
    .stDownloadButton button, .stButton button { 
        width: 100%; border-radius: 6px; background-color: transparent !important; 
        color: #00E6FF !important; border: 1px solid #00E6FF !important; 
        font-weight: 600; transition: 0.3s ease;
    }
    .stDownloadButton button:hover, .stButton button:hover { 
        background-color: #00E6FF !important; color: #000000 !important; 
        box-shadow: 0 0 15px rgba(0, 230, 255, 0.3);
    }
    
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- INYECCIÓN DE MOTOR DE VOZ (API NATIVA) ---
voice_js = """
<script>
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'es-ES';
    recognition.continuous = false;

    window.parent.document.addEventListener('start_dictation', () => {
        recognition.start();
    });

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        const input = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (input) {
            input.value = text;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    window.parent.document.addEventListener('speak_text', (e) => {
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance(e.detail.text);
        msg.lang = 'es-ES';
        msg.rate = 1.0;
        window.speechSynthesis.speak(msg);
    });
</script>
"""
st.components.v1.html(voice_js, height=0)

# --- 2. CONFIGURACIÓN DE MODELO ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 API Key faltante en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y sostenibilidad.",
    "Director Centro Telemedicina": "Innovación y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión académica y normativa.",
    "Director de UCI": "Rigor clínico y medicina crítica.",
    "Investigador Científico": "Metodología y APA 7.",
    "Consultor Salud Digital": "Estrategia e interculturalidad.",
    "Professor Universitario": "Pedagogía y mentoría.",
    "Estratega de Trading": "Gestión de riesgo y mercados."
}

# --- 3. FUNCIONES DE PROCESAMIENTO ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])

def clean_txt(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#+\s*', '', text)
    return text.strip()

# --- 4. MOTOR DE EXPORTACIÓN ROBUSTO ---
def export_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Reporte IkigAI: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()} | Confidencial").italic = True
    for line in content.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('#'):
            doc.add_heading(clean_txt(line), level=2)
        else:
            doc.add_paragraph(clean_txt(line))
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def export_pptx(content, role):
    prs = Presentation()
    segments = [clean_txt(s) for s in re.split(r'\n|\. ', content) if len(s.strip()) > 30]
    # Portada
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = role.upper()
    slide.placeholders[1].text = f"Análisis Estratégico IkigAI\n{date.today()}"
    # Diapositivas
    for i, seg in enumerate(segments[:12]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Pilar {i+1}"
        slide.placeholders[1].text = (seg[:445] + "...") if len(seg) > 450 else seg
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 5. GESTIÓN DE ESTADO ---
for key in ["biblioteca", "messages", "last_analysis"]:
    if key not in st.session_state:
        if key == "biblioteca": st.session_state[key] = {r: "" for r in ROLES}
        elif key == "messages": st.session_state[key] = []
        else: st.session_state[key] = ""

# --- 6. BARRA LATERAL (ZEN ESTRATÉGICO) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px; margin-bottom: 0;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px; margin-top: 0;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    if st.button("🗑️ REINICIAR ENGINE"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    st.divider()
    st.markdown("<div class='section-tag'>PERFIL</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    if st.session_state.last_analysis:
        st.divider()
        st.markdown("<div class='section-tag'>EXPORTAR</div>", unsafe_allow_html=True)
        st.download_button("📄 WORD LIMPIO", data=export_word(st.session_state.last_analysis, rol_activo), file_name=f"{rol_activo}_Report.docx")
        st.download_button("📊 POWERPOINT", data=export_pptx(st.session_state.last_analysis, rol_activo), file_name=f"{rol_activo}_Deck.pptx")

    st.divider()
    st.markdown("<div class='section-tag'>FUENTES</div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["DOC", "URL", "IMG"])
    with t1:
        up = st.file_uploader("Carga:", type=['pdf', 'docx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 PROCESAR", use_container_width=True):
            for f in up:
                st.session_state.biblioteca[rol_activo] += get_pdf_text(f) if f.type == "application/pdf" else get_docx_text(f)
            st.success("Analizado.")
    with t2:
        url = st.text_input("URL:", placeholder="https://")
        if st.button("🔗 CONECTAR", use_container_width=True):
            r = requests.get(url, timeout=10)
            st.session_state.biblioteca[rol_activo] += BeautifulSoup(r.text, 'html.parser').get_text()
            st.success("Listo.")
    with t3:
        img = st.file_uploader("Imagen:", type=['jpg', 'png'], label_visibility="collapsed")
        if img: st.image(img)

# --- 7. PANEL CENTRAL ---
st.markdown(f"<h3 style='color: #00A3FF; margin-bottom: 20px;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

# Controles de Audio
c_v1, c_v2 = st.columns(2)
with c_v1:
    if st.button("🎙️ INICIAR DICTADO"):
        st.write('<script>window.parent.document.dispatchEvent(new CustomEvent("start_dictation"));</script>', unsafe_allow_html=True)
with c_v2:
    if st.button("🔇 SILENCIAR"):
        st.write('<script>window.speechSynthesis.cancel();</script>', unsafe_allow_html=True)

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            col_a, col_b = st.columns([1, 4])
            with col_a:
                if st.button("📋", key=f"c_{i}"):
                    st.write(f'<script>navigator.clipboard.writeText(`{m["content"]}`);</script>', unsafe_allow_html=True)
                    st.toast("Copiado")
            with col_b:
                if st.button("🔊 LEER", key=f"l_{i}"):
                    clean_msg = clean_txt(m["content"])
                    st.write(f'<script>window.parent.document.dispatchEvent(new CustomEvent("speak_text", {{detail: {{text: `{clean_msg}`}}}}));</script>', unsafe_allow_html=True)

if pr := st.chat_input("Escriba o use el dictado..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        ctx = f"Rol: {rol_activo}. Contexto: {st.session_state.biblioteca[rol_activo][:500000]}. Estilo clínico, ejecutivo. APA 7."
        resp = model.generate_content([ctx, pr])
        st.session_state.last_analysis = resp.text
        st.markdown(resp.text)
        st.session_state.messages.append({"role": "assistant", "content": resp.text})
        st.rerun()
