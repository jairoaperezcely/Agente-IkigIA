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
from gtts import gTTS
import os
import re
from audio_recorder_streamlit import audio_recorder # Requiere: pip install audio-recorder-streamlit

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="IkigAI V1.40 - Bimodal Strategy Hub", page_icon="🧬", layout="wide")

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

# --- 3. FUNCIONES DE EXPORTACIÓN Y VOZ ---
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
        slide.shapes.title.text = f"Eje {i+1}"; slide.placeholders[1].text = p[:500]
    bio = BytesIO(); prs.save(bio); return bio.getvalue()

# --- 4. LÓGICA DE MEMORIA ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Rol Estratégico:", list(ROLES.keys()))
    st.session_state.rol_actual = rol_activo
    
    st.divider()
    st.subheader("🎙️ Interacción de Voz")
    voz_activa = st.toggle("Habilitar Lectura de Respuesta", value=True)
    
    st.write("Dictar instrucción:")
    audio_bytes = audio_recorder(text="", icon_size="2x", neutral_color="#2E86C1")
    
    st.divider()
    st.subheader("💾 Exportar")
    if st.session_state.last_analysis:
        st.download_button("📄 Word (APA 7)", data=download_word(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.docx")
        st.download_button("📊 PowerPoint", data=download_pptx(st.session_state.last_analysis, rol_activo), file_name=f"IkigAI_{rol_activo}.pptx")

    st.divider()
    t1, t2, t3 = st.tabs(["📄 Archivos", "🔗 Enlaces", "🖼️ Img"])
    with t1:
        up = st.file_uploader("Cargar:", type=['pdf', 'docx', 'xlsx'], accept_multiple_files=True)
        if st.button("🧠 Procesar"):
            for f in up:
                if f.type == "application/pdf": st.session_state.biblioteca[rol_activo] += get_pdf_text(f)
                elif "word" in f.type: st.session_state.biblioteca[rol_activo] += get_docx_text(f)
                elif "sheet" in f.type: st.session_state.biblioteca[rol_activo] += get_excel_text(f)
            st.success("Leído.")
    with t2:
        uw, uy = st.text_input("URL Web:"), st.text_input("URL YouTube:")
        if st.button("🌐 Conectar"):
            if uw: st.session_state.biblioteca[rol_activo] += get_web_text(uw)
            if uy: st.session_state.biblioteca[rol_activo] += get_yt_text(uy)
            st.success("Conectado.")
    with t3:
        img_f = st.file_uploader("Imagen:", type=['jpg', 'png'])
        if img_f: st.image(img_f); st.session_state.temp_image = Image.open(img_f)

# --- 6. PROCESAMIENTO DE AUDIO A TEXTO ---
prompt_final = None
if audio_bytes:
    with st.spinner("Transcribiendo audio..."):
        # Se envía el audio a Gemini para transcripción y procesamiento directo
        audio_bio = BytesIO(audio_bytes)
        audio_bio.name = "audio.wav"
        model_transcribe = genai.GenerativeModel('gemini-1.5-flash')
        res_voice = model_transcribe.generate_content([
            "Transcribe este audio a texto en español de forma exacta.",
            {"mime_type": "audio/wav", "data": audio_bytes}
        ])
        prompt_final = res_voice.text

# --- 7. PANEL CENTRAL ---
st.header(f"IkigAI: {rol_activo}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# Prioriza el audio si existe, si no, usa el chat input
chat_input = st.chat_input("Escriba su instrucción...")
if prompt_final or chat_input:
    pr = prompt_final if prompt_final else chat_input
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-2.5-flash')
        sys = f"Identidad: IkigAI - {rol_activo}. {ROLES[rol_activo]}. Estilo clínico, ejecutivo. Referencias APA 7."
        inputs = [sys, f"Contexto: {st.session_state.biblioteca[rol_activo][:500000]}", pr]
        if "temp_image" in st.session_state and st.session_state.temp_image: 
            inputs.append(st.session_state.temp_image)
        
        res = model.generate_content(inputs)
        st.session_state.last_analysis = res.text
        st.markdown(res.text)
        
        if voz_activa:
            clean_txt = re.sub(r'[*#_>-]', '', res.text)
            tts = gTTS(text=clean_txt, lang='es', tld='com.mx')
            fp = BytesIO(); tts.write_to_fp(fp); fp.seek(0)
            st.audio(fp, format="audio/mp3")
            
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.session_state.temp_image = None
        st.rerun()
