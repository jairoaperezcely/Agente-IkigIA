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
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD (8 ROLES) ---
st.set_page_config(page_title="IkigAI V1.14 - Sistema Operativo Integral", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y sostenibilidad del líder.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión y normativa Facultad de Medicina UNAL.",
    "Director de UCI": "Rigor clínico y datos en el HUN.",
    "Investigador Científico": "Metodología y redacción científica de alto impacto.",
    "Consultor Salud Digital": "Estrategia BID/MinSalud y territorio.",
    "Profesor Universitario": "Pedagogía y mentoría médica.",
    "Estratega de Trading": "Gestión de riesgo y psicología de mercado."
}

# --- 2. FUNCIONES DE LECTURA (Restauradas) ---
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

# --- 3. FUNCIONES DE ESCRITURA (Nuevo - Entregables Elegantes) ---
def create_word_doc(title, content):
    doc = docx.Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Generado por IkigAI - {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Contexto: {st.session_state.rol_actual}")
    for p in content.split('\n'):
        if p.strip(): doc.add_paragraph(p)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state:
    st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "temp_image" not in st.session_state: st.session_state.temp_image = None
if "last_response" not in st.session_state: st.session_state.last_response = ""

# --- 5. BARRA LATERAL: FUENTES Y ROLES (Restaurado y Ampliado) ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Cambiar Rol Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    
    st.divider()
    st.subheader(f"🔌 Fuentes para {rol_activo}")
    
    tab_files, tab_links, tab_images = st.tabs(["📄 Archivos", "🔗 Links", "🖼️ Imágenes"])
    
    with tab_files:
        up_files = st.file_uploader("Leer PDF, Word, Excel:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Leer Documentos"):
            for f in up_files:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif f.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document": st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif f.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Documentos leídos correctamente.")

    with tab_links:
        url_w = st.text_input("URL Web:")
        url_y = st.text_input("URL YouTube:")
        if st.button("🌐 Leer Links"):
            if url_w: st.session_state.biblioteca[rol_activo] += get_web_text(url_w)
            if url_y: st.session_state.biblioteca[rol_activo] += get_yt_text(url_y)
            st.success("Fuentes externas leídas.")

    with tab_images:
        img_file = st.file_uploader("Leer imagen (JPG, PNG):", type=['jpg', 'jpeg', 'png'])
        if img_file:
            st.session_state.temp_image = Image.open(img_file)
            st.image(st.session_state.temp_image, caption="Imagen cargada", use_container_width=True)

    st.divider()
    st.subheader("💾 Exportar Entregable")
    if st.session_state.last_response:
        st.download_button("📄 Descargar en Word", 
                           data=create_word_doc(f"Informe IkigAI - {rol_activo}", st.session_state.last_response),
                           file_name=f"IkigAI_{rol_activo}_{date.today()}.docx")
    
    if st.button("🗑️ Reiniciar Sesión"):
        st.session_state.messages = []
        st.rerun()

# --- 6. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

with st.expander("🚀 Módulo de ROI Cognitivo"):
    tareas = st.text_area("Objetivos de hoy:", placeholder="Escriba sus tareas para priorizar...")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("¿Qué estrategia diseñamos hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-1.5-pro')
        system_p = f"""IDENTIDAD: IkigAI - {rol_activo}. {ROLES[rol_activo]}
        BIBLIOTECA LEÍDA: {st.session_state.biblioteca[rol_activo][:500000]}
        REGLAS: Estilo ejecutivo, clínico, directo. Sin clichés. Si pides documento, hazlo elegante."""
        
        inputs = [system_p, prompt]
        if st.session_state.temp_image: inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.session_state.last_response = res.text
        st.markdown(res.text)
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.session_state.temp_image = None
