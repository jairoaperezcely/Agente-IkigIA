import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente Médico V5.6 (Auto-Lectura)", page_icon="🧬", layout="wide")

# --- FUNCIONES DE LECTURA ---
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def get_youtube_text(video_url):
    try:
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be" in video_url:
            video_id = video_url.split("/")[-1]
        else:
            return "URL inválida."
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        text = " ".join([entry['text'] for entry in transcript])
        return f"TRANSCRIPCIÓN YOUTUBE:\n{text}"
    except:
        return "No se pudo obtener la transcripción."

def get_web_text(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = "\n".join([p.get_text() for p in paragraphs])
        return f"CONTENIDO WEB ({url}):\n{text}"
    except Exception as e:
        return f"Error web: {str(e)}"

# --- LÓGICA DE MEMORIA ---
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_video_gemini" not in st.session_state: st.session_state.archivo_video_gemini = None
if "last_uploaded_file" not in st.session_state: st.session_state.last_uploaded_file = None

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    
    st.divider()
    
    rol = st.radio("Perfil Activo:", [
        "Vicedecano Académico", 
        "Director de UCI", 
        "Experto en Telesalud",
        "Investigador Científico",
        "Profesor universitario",
        "Asistente Personal",
        "Mentor de Trading"
    ])
    
    st.divider()
    st.subheader("📥 Cargar Información")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Doc", "📹 MP4", "🔴 YT", "🌐 Web"])
    
    # 1. Documentos (AHORA AUTOMÁTICO)
    with tab1:
        uploaded_doc = st.file_uploader("Subir PDF/Word", type=['pdf', 'docx'])
        # Lógica de auto-lectura: si hay archivo y es diferente al anterior, léelo.
        if uploaded_doc:
            if st.session_state.last_uploaded_file != uploaded_doc.name:
                with st.spinner("Leyendo documento automáticamente..."):
                    if uploaded_doc.type == "application/pdf":
                        st.session_state.contexto_texto = get_pdf_text(uploaded_doc)
                    else:
                        st.session_state.contexto_texto = get_docx_text(uploaded_doc)
                    
                    st.session_state.last_uploaded_file = uploaded_doc.name
                    st.success(f"✅ Documento leído: {uploaded_doc.name}")
            else:
                st.info(f"📂 Archivo activo: {uploaded_doc.name}")

    # 2. Video Nativo
    with tab2:
        uploaded_video = st.file_uploader("Subir Video (.mp4)", type=['mp4', 'mov'])
        if uploaded_video and api_key and st.button("👁️ Analizar Video"):
            genai.configure(api_key=api_key)
            with st.spinner("Subiendo video a Gemini 2.5..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    tmp_file.write(uploaded_video.read())
                    tmp_path = tmp_file.name
                video_file = genai.upload_file(path=tmp_path)
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = genai.get_file(video_file.name)
                st.session_state.archivo_video_gemini = video_file
                st.success("✅ Video listo")
                os.remove(tmp_path)

    # 3. YouTube
    with tab3:
        yt_url = st.text_input("Link YouTube:")
        if yt_url and st.button("Leer YouTube"):
            st.session_state.contexto_texto = get_youtube_text(yt_url)
            st.success("✅ Transcripción cargada")

    # 4. Web
    with tab4:
        web_url = st.text_input("Link Web:")
        if web_url and st.button("Leer Web"):
            st.session_state.contexto_texto = get_web_text(web_url)
            st.success("✅ Web cargada")

    st.divider()
    if st.button("🗑️ Borrar Memoria"):
        st.session_state.messages = []
        st.session_state.contexto_texto = ""
        st.session_state.archivo_video_gemini = None
        st.session_state.last_uploaded_file = None
        st.rerun()

# --- CHAT ---
st.title(f"🤖 Agente: {rol}")

if not api_key:
    st.warning("⚠️ Ingrese API Key.")
    st.stop()

genai.configure(api_key=api_key)
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("Error cargando modelo.")
    st.stop()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escriba su consulta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                contenido = []
                instruccion = f"Actúa como {rol}."
                
                # INYECTAR DOCUMENTO EXPLÍCITAMENTE
                if st.session_state.contexto_texto:
                    instruccion += f"\n\n--- INICIO DOCUMENTO ADJUNTO ---\n{st.session_state.contexto_texto[:40000]}\n--- FIN DOCUMENTO ---\nResponde basándote en este documento."
                else:
                    instruccion += "\n(No hay documento adjunto por el momento)."

                if st.session_state.archivo_video_gemini:
                    contenido.append(st.session_state.archivo_video_gemini)
                    instruccion += " (Analiza el video adjunto)."

                # Historial reciente
                historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                instruccion += f"\n\nHISTORIAL:\n{historial}\n\nPREGUNTA USUARIO: {prompt}"

                contenido.append(instruccion)
                
                response = model.generate_content(contenido)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Error: {e}")
