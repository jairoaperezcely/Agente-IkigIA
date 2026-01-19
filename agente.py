import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from pypdf import PdfReader
from docx import Document
from bs4 import BeautifulSoup
import requests
import tempfile
import time
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Agente Académico 2.5", page_icon="🧬", layout="wide")
st.title("🧬 Su Asistente Personal (Motor v2.5)")

api_key = st.sidebar.text_input("Ingrese su API Key de Gemini:", type="password")
if api_key:
    genai.configure(api_key=api_key)

# --- MOTOR IA ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Motor de Inteligencia")
modelos_disponibles = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-flash-latest"]
modelo_usar = st.sidebar.selectbox("Seleccione Modelo:", modelos_disponibles)

# --- ROLES ---
st.sidebar.markdown("---")
st.sidebar.header("1. ¿Quién soy hoy?")
roles_disponibles = [
    "Vicedecano Académico (Gestión)", 
    "Director de UCI (Clínico)", 
    "Experto en Telesalud (Tecnología)", 
    "Profesor Universitario (Docencia)",
    "Redactor Científico (Papers)",
    "Mentor de Trading (Educativo)",
    "Coach de Productividad (Agenda)"
]
rol_seleccionado = st.sidebar.selectbox("Seleccione su modo:", roles_disponibles)

prompts_roles = {
    "Vicedecano Académico (Gestión)": "Eres el Vicedecano. Tono: Formal, jurídico, institucional.",
    "Director de UCI (Clínico)": "Eres Director de UCI. Tono: Técnico, directo, EBM.",
    "Experto en Telesalud (Tecnología)": "Eres experto en Salud Digital. Tono: Innovador y técnico.",
    "Profesor Universitario (Docencia)": "Eres Docente. Tono: Pedagógico y claro.",
    "Redactor Científico (Papers)": "Eres Editor Médico Q1. Tono: Académico, IMRaD.",
    "Mentor de Trading (Educativo)": "Eres Mentor de Trading. NO das consejos de inversión. Tono: Educativo.",
    "Coach de Productividad (Agenda)": "Eres Coach de Productividad. Usa Time Blocking y Matriz Eisenhower."
}

# --- FUNCIONES ---
def leer_pdf(f):
    try:
        reader = PdfReader(f)
        text = ""
        for page in reader.pages: text += page.extract_text() or ""
        return text
    except: return ""

def leer_word(f):
    try: return "\n".join([p.text for p in Document(f).paragraphs])
    except: return ""

def leer_url(u):
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(u, headers=h, timeout=5)
        if r.status_code == 200:
            s = BeautifulSoup(r.content, 'html.parser')
            for tag in s(["script", "style"]): tag.decompose()
            return s.get_text(separator='\n')
        return ""
    except: return ""

def procesar_video(f):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as t:
        t.write(f.read())
        path = t.name
    try:
        v = genai.upload_file(path=path)
        while v.state.name == "PROCESSING":
            time.sleep(1)
            v = genai.get_file(v.name)
        return v
    except: return None
    finally: os.remove(path)

# --- INTERFAZ DE ENTRADA ---
st.sidebar.markdown("---")
st.sidebar.header("2. Material (Opcional)")
# AQUI AGREGAMOS LA OPCIÓN "CHAT LIBRE"
tipo_fuente = st.sidebar.radio("Origen:", ["Chat Libre (Sin Archivo)", "Archivo (PDF/Word)", "Video (MP4)", "Web (URL)"])

contenido = ""
tipo_contenido = "texto"

if tipo_fuente == "Archivo (PDF/Word)":
    arch = st.sidebar.file_uploader("Subir", type=["pdf", "docx"])
    if arch: contenido = leer_pdf(arch) if arch.name.endswith(".pdf") else leer_word(arch)

elif tipo_fuente == "Video (MP4)":
    arch = st.sidebar.file_uploader("Subir video", type=["mp4"])
    if arch and api_key:
        contenido = procesar_video(arch)
        tipo_contenido = "video"

elif tipo_fuente == "Web (URL)":
    url = st.sidebar.text_input("Link:")
    if url: contenido = leer_url(url)

# --- EJECUCIÓN ---
st.markdown(f"### 🎯 Modo: **{rol_seleccionado}**")
consulta = st.text_area("Instrucción:", height=150)

if st.button("Ejecutar") and api_key and consulta:
    with st.spinner(f"Usando {modelo_usar}..."):
        try:
            model = genai.GenerativeModel(modelo_usar, system_instruction=prompts_roles[rol_seleccionado])
            
            # Lógica Inteligente: ¿Hay archivo o es chat puro?
            if tipo_contenido == "video" and contenido:
                prompt = f"Analiza esto: {consulta}"
                res = model.generate_content([contenido, prompt]).text
            elif contenido and tipo_contenido == "texto":
                prompt = f"CONTEXTO:\n{contenido[:30000]}\n\nPREGUNTA:\n{consulta}"
                res = model.generate_content(prompt).text
            else:
                # MODO CHAT LIBRE (Sin contexto)
                res = model.generate_content(consulta).text
                
            st.markdown(res)
        except Exception as e:
            st.error(f"Error: {e}")