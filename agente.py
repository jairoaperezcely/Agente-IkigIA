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
import os
import re

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(
    page_title="IkigAI V1.43 - Executive Design Center", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS para mejorar la estética en móviles y escritorio
st.markdown("""
    <style>
    .stDownloadButton button { width: 100%; border-radius: 8px; height: 3em; background-color: #f0f2f6; border: 1px solid #d1d8e0; }
    .stDownloadButton button:hover { background-color: #e0e4eb; border-color: #2E86C1; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y eliminación de procastinación.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión y normativa Facultad de Medicina UNAL.",
    "Director de UCI": "Rigor clínico y datos en el HUN.",
    "Investigador Científico": "Metodología y redacción científica (APA 7).",
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Professor Universitario": "Pedagogía disruptiva y mentoría médica.",
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

# --- 3. MOTOR DE EXPORTACIÓN OFFICE ---
def download_word(content, role):
    doc = docx.Document()
    doc.add_heading(f'Entregable IkigAI: {role}', 0)
    doc.add_paragraph(f"Fecha: {date.today()} | Formato APA 7").italic = True
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = f"Estrategia {role}"
    slide.placeholders[1].text = f"IkigAI Engine - {date.today()}"
    points = [p for p in content.split('\n') if len(p.strip()) > 30]
    for i, p in enumerate(points[:8]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Eje {i+1}"; slide.placeholders[1].text = p[:500]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "temp_image" not in st.session_state: st.session_state.temp_image = None

# --- 5. BARRA LATERAL (DISEÑO PREMIUM MÉXICO/COLOMBIA) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Universidad_Nacional_de_Colombia_Logo.svg/1200px-Universidad_Nacional_de_Colombia_Logo.svg.png", width=80)
    st.title("🧬 IkigAI Engine")
    st.caption("Executive Design Center | V1.43")
    
    rol_activo = st.selectbox("🎯 Perfil Activo:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    
    # SECCIÓN DE EXPORTACIÓN (Prioridad Alta)
    if st.session_state.last_analysis:
        st.divider()
        st.subheader("💾 Exportar Informe")
        st.download_button("📄 Formato Word (APA 7)", 
                           data=download_word(st.session_state.last_analysis, rol_activo), 
                           file_name=f"IkigAI_{rol_activo}_{date.today()}.docx")
        st.download_button("📊 Presentación PPTX", 
                           data=download_pptx(st.session_state.last_analysis, rol_activo), 
                           file_name=f"IkigAI_{rol_activo}_{date.today()}.pptx")

    st.divider()
    st.subheader("🔌 Fuentes de Datos")
    tab_files, tab_links, tab_img = st.tabs(["📄 Doc", "🔗 Link", "🖼️ Img"])
    
    with tab_files:
        up = st.file_uploader("Subir PDF/Docs:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 Procesar Archivos", use_container_width=True):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Datos integrados.")

    with tab_links:
        uw = st.text_input("URL Web:", placeholder="https://...")
        uy = st.text_input("URL YouTube:", placeholder="https://youtube.com/...")
        if st.button("🌐 Conectar Fuentes", use_container_width=True):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Links conectados.")

    with tab_img:
        img_f = st.file_uploader("Analizar Imagen:", type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")
        if img_f:
            st.session_state.temp_image = Image.open(img_f)
            st.image(img_f, caption="Imagen cargada")

# --- 6. PANEL CENTRAL (CHAT EJECUTIVO) ---
st.header(f"IkigAI: {rol_activo}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): 
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            # Botón de copiado simple integrado por Markdown para mayor compatibilidad
            st.button("📋 Copiar respuesta", key=f"btn_{st.session_state.messages.index(msg)}", 
                      on_click=lambda text=msg["content"]: st.write(f'<script>navigator.clipboard.writeText(`{text}`)</script>', unsafe_allow_html=True))

if pr := st.chat_input("¿Qué diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        # Usamos gemini-1.5-flash por ser el identificador más estable en la API
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys_context = f"""Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. 
        Estilo clínico, directo y humano. Sin clichés. Citas y bibliografía estrictamente en APA 7."""
        
        content_to_send = [sys_context, f"Contexto acumulado: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if st.session_state.temp_image: content_to_send.append(st.session_state.temp_image)
        
        response = model.generate_content(content_to_send)
        st.session_state.last_analysis = response.text
        st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.session_state.temp_image = None # Limpia imagen tras uso
        st.rerun() # Actualiza barra lateral para mostrar descargas
