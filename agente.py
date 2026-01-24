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

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(
    page_title="IkigAI V1.72 - Sidebar Voice Hub", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS V1.72: Zen con Botones de Voz Blindados
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    
    /* Botones de Acción Estilo Zen */
    .stDownloadButton button, .stButton button { 
        width: 100%; border-radius: 4px; background-color: transparent !important; 
        color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; 
    }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; }
    
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; }
    blockquote { border-left: 4px solid #00E6FF !important; background-color: #0D1117 !important; padding: 15px !important; }
    
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1px; margin-top: 15px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- PUENTE JAVASCRIPT ROBUSTO ---
st.components.v1.html("""
<script>
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'es-ES';
    recognition.continuous = false;

    window.parent.document.addEventListener('INICIAR_MIC', () => {
        recognition.start();
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const chatInput = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (chatInput) {
            chatInput.value = transcript;
            chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    window.parent.document.addEventListener('LEER_RESPUESTA', (e) => {
        window.speechSynthesis.cancel();
        const msg = new SpeechSynthesisUtterance(e.detail.text);
        msg.lang = 'es-ES';
        window.speechSynthesis.speak(msg);
    });
</script>
""", height=0)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure API Key.")
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

# --- 2. FUNCIONES BASE ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def clean_txt(text): return re.sub(r'\*+', '', text).strip()

def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'IkigAI Report: {role}', 0)
    for line in content.split('\n'):
        if line.strip(): doc.add_paragraph(clean_txt(line))
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    segments = [clean_txt(s) for s in re.split(r'\n|\. ', content) if len(s.strip()) > 30]
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = role.upper()
    for i, seg in enumerate(segments[:12]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje {i+1}"; slide.placeholders[1].text = seg[:450]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 3. GESTIÓN DE ESTADO ---
if "messages" not in st.session_state: st.session_state.messages = []
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {r: "" for r in ROLES}
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 4. BARRA LATERAL (CONTROL TOTAL) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    # CONTROL DE VOZ INTEGRADO EN SIDEBAR
    st.divider()
    st.markdown("<div class='section-tag'>CONTROLES DE VOZ</div>", unsafe_allow_html=True)
    if st.button("🎙️ DICTAR (MICRÓFONO)"):
        st.write('<script>window.parent.document.dispatchEvent(new CustomEvent("INICIAR_MIC"));</script>', unsafe_allow_html=True)
    if st.button("🔇 SILENCIAR"):
        st.write('<script>window.speechSynthesis.cancel();</script>', unsafe_allow_html=True)

    st.divider()
    st.markdown("<div class='section-tag'>PERFIL ESTRATÉGICO</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    if st.session_state.last_analysis:
        st.divider()
        st.markdown("<div class='section-tag'>EXPORTAR</div>", unsafe_allow_html=True)
        st.download_button("📄 WORD (CLEAN)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"Report_{rol_activo}.docx")
        st.download_button("📊 POWERPOINT", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"Deck_{rol_activo}.pptx")

    st.divider()
    st.markdown("<div class='section-tag'>FUENTES DE DATOS</div>", unsafe_allow_html=True)
    up = st.file_uploader("Subir:", type=['pdf', 'docx'], accept_multiple_files=True, label_visibility="collapsed")
    if st.button("🧠 PROCESAR"):
        for f in up:
            st.session_state.biblioteca[rol_activo] += get_pdf_text(f) if f.type == "application/pdf" else get_docx_text(f)
        st.success("Listo.")
    
    st.divider()
    if st.button("🗑️ REINICIAR ENGINE"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# --- 5. PANEL CENTRAL ---
st.markdown(f"<h3 style='color: #00A3FF;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🔊 LEER", key=f"v_{i}"):
                    clean_msg = clean_txt(m["content"]).replace('"', "'")
                    st.write(f'<script>window.parent.document.dispatchEvent(new CustomEvent("LEER_RESPUESTA", {{detail: {{text: "{clean_msg}"}}}}));</script>', unsafe_allow_html=True)
            with c2:
                if st.button("📋 COPIAR", key=f"c_{i}"):
                    st.write(f'<script>navigator.clipboard.writeText(`{m["content"]}`);</script>', unsafe_allow_html=True)
                    st.toast("Copiado")

if pr := st.chat_input("Escriba o use el dictado de la izquierda..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        ctx = f"Identidad: {rol_activo}. Estilo ejecutivo, clínico. APA 7."
        resp = model.generate_content([ctx, f"Docs: {st.session_state.biblioteca[rol_activo][:500000]}", pr])
        st.session_state.last_analysis = resp.text
        st.markdown(resp.text)
        st.session_state.messages.append({"role": "assistant", "content": resp.text})
        st.rerun()
