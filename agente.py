import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import os
import time
from datetime import date

# --- CONFIGURACIÓN Y AUTENTICACIÓN ---
st.set_page_config(page_title="Coach Alto Desempeño V11", page_icon="📈", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Configura 'GOOGLE_API_KEY' en los secretos de Streamlit.")
    st.stop()

# --- FUNCIONES DE EXTRACCIÓN DE CONTENIDO ---

def get_web_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return "\n".join([p.get_text() for p in paragraphs])
    except Exception as e:
        return f"Error al leer web: {e}"

def get_youtube_transcript(url):
    try:
        video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        return f"Error al obtener transcripción de YouTube: {e}"

# --- LÓGICA DE ESTADO ---
if "messages" not in st.session_state: st.session_state.messages = []
if "global_context" not in st.session_state: st.session_state.global_context = ""

# --- BARRA LATERAL (ENTRADAS DE DATOS) ---
with st.sidebar:
    st.header("🔌 Conectores de Datos")
    
    # 1. Entrada Web
    web_url = st.text_input("🔗 URL Página Web:")
    if st.button("Leer Web") and web_url:
        with st.spinner("Extrayendo texto..."):
            st.session_state.global_context += f"\n[CONTENIDO WEB]: {get_web_content(web_url)}"
            st.success("Web cargada.")

    # 2. Entrada YouTube
    yt_url = st.text_input("🎥 URL YouTube:")
    if st.button("Leer YouTube") and yt_url:
        with st.spinner("Procesando transcripción..."):
            st.session_state.global_context += f"\n[TRANSCRIPCIÓN YT]: {get_youtube_transcript(yt_url)}"
            st.success("Video cargado.")

    # 3. Subida de Archivos Multimedia (Video/Audio)
    uploaded_media = st.file_uploader("📁 Video/Audio/Imagen", type=['mp4', 'mp3', 'png', 'jpg'])
    
    st.divider()
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state.global_context = ""
        st.session_state.messages = []
        st.rerun()

# --- CHAT PRINCIPAL ---
st.title("🤖 Coach de Alto Desempeño Integral")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("¿Cuál es el plan para hoy?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Usamos Gemini 1.5 Pro para análisis profundo de video y texto
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Construcción del Prompt con el contexto acumulado
            full_prompt = f"""
            ROL: Coach Personal de Alto Desempeño.
            FECHA: {date.today()}
            CONTEXTO ACUMULADO (Web/YT/Docs): {st.session_state.global_context[-500000:]}
            
            INSTRUCCIÓN: Analiza la solicitud basándote en el contexto. 
            Identifica procrastinación y ofrece una dinámica de pensamiento crítico.
            
            SOLICITUD: {prompt}
            """
            
            # Manejo de archivo multimedia si existe
            if uploaded_media:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_media.name)[1]) as tmp:
                    tmp.write(uploaded_media.read())
                    file_to_genai = genai.upload_file(path=tmp.name)
                
                # Esperar procesamiento del video si es necesario
                while file_to_genai.state.name == "PROCESSING":
                    time.sleep(2)
                    file_to_genai = genai.get_file(file_to_genai.name)
                
                response = model.generate_content([file_to_genai, full_prompt])
            else:
                response = model.generate_content(full_prompt)

            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Error: {e}")
