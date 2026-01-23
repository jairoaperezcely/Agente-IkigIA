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
from io import BytesIO
import json
from datetime import date

# Módulos utilitarios para lectura de documentos y creación de actas
from utils.document_reader import get_pdf_text, get_docx_text
from utils.media_handler import process_uploaded_media
from utils.web_reader import get_web_text, get_youtube_text
from utils.session_memory import reset_session, load_backup, save_chat_to_docx
from utils.prompts import prompts_roles, create_instruccion

# Configuración inicial
st.set_page_config(page_title="Agente IA Multimodal v9.5", page_icon="🧬", layout="wide")

# Inicialización del estado
for key in ["messages", "contexto_texto", "archivo_multimodal", "info_archivos"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "messages" else ""

# Sidebar: Configuración de usuario
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2, 0.1)
    rol = st.radio("Perfil Activo:", list(prompts_roles.keys()))

    if st.session_state["messages"]:
        col1, col2 = st.columns(2)
        docx_file = save_chat_to_docx(st.session_state["messages"])
        col1.download_button("📄 Acta", docx_file, "acta_sesion.docx")
        chat_json = json.dumps(st.session_state["messages"])
        col2.download_button("🧠 Backup", chat_json, "memoria.json")

    uploaded_memory = st.file_uploader("Restaurar (.json)", type=['json'])
    if uploaded_memory and st.button("🔄 Cargar Memoria"):
        load_backup(uploaded_memory)

    if st.button("🗑️ Nueva Sesión"):
        reset_session()

# Carga de fuentes: Archivos, media, YouTube, Web
with st.sidebar.expander("📥 Carga de Fuentes"):
    uploaded_docs = st.file_uploader("📚 Documentos (PDF/DOCX)", type=['pdf', 'docx'], accept_multiple_files=True)
    if uploaded_docs and st.button("🧠 Procesar Archivos"):
        texto_acumulado = ""
        for doc in uploaded_docs:
            contenido = get_pdf_text(doc) if doc.type == "application/pdf" else get_docx_text(doc)
            texto_acumulado += f"\n--- {doc.name} ---\n{contenido}\n"
        st.session_state.contexto_texto = texto_acumulado
        st.session_state.info_archivos = f"{len(uploaded_docs)} archivos procesados."

    media_file = st.file_uploader("🎥 Media (video/audio/imagen)", type=['mp4','mp3','wav','m4a','png','jpg','jpeg'])
    if media_file and api_key and st.button("Procesar Media"):
        archivo_multimodal = process_uploaded_media(media_file, api_key)
        st.session_state.archivo_multimodal = archivo_multimodal

    yt_url = st.text_input("🔴 Link YouTube")
    if yt_url and st.button("Cargar YouTube"):
        st.session_state.contexto_texto = get_youtube_text(yt_url)

    web_url = st.text_input("🌐 Link Web")
    if web_url and st.button("Cargar Web"):
        st.session_state.contexto_texto = get_web_text(web_url)

# Validación de API
if not api_key:
    st.warning("⚠️ Ingrese una API Key para continuar.")
    st.stop()

# Configuración del modelo
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"temperature": temp_val})

# Título y despliegue del historial
st.title(f"🤖 Agente IA: {rol}")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada de usuario
if prompt := st.chat_input("Escriba su instrucción..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            try:
                instruccion = create_instruccion(rol, prompts_roles[rol], st.session_state.contexto_texto, prompt, st.session_state.messages, st.session_state.archivo_multimodal)
                contenido = [instruccion]
                if st.session_state.archivo_multimodal:
                    contenido.append(st.session_state.archivo_multimodal)

                response = model.generate_content(contenido)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
