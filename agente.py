import sys
import os
import json
import re
import requests
import pandas as pd
import docx
import google.generativeai as genai
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from datetime import date, datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(
    page_title="IkigAI V1.92 - Omni-Vision Workstation", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Zen: Contraste Quirúrgico y Ergonomía Móvil
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, h1, h2, h3 { color: #FFFFFF !important; }
    [data-testid="stChatMessage"] { background-color: #050505 !important; border: 1px solid #1A1A1A !important; }
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    .stDownloadButton button, .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; }
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; text-transform: uppercase; }
    .stExpander { border: 1px solid #1A1A1A !important; background-color: #050505 !important; border-radius: 8px !important; }
    textarea { background-color: #0D1117 !important; color: #FFFFFF !important; border: 1px solid #00E6FF !important; font-family: 'Courier New', monospace !important; }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key en st.secrets.")
    st.stop()

ROLES = {
    "Coach de Alto Desempeño": "ROI cognitivo y sostenibilidad administrativa.",
    "Director Centro Telemedicina": "Innovación, IA y Salud Digital UNAL.",
    "Vicedecano Académico": "Gestión académica, normativa y MD-PhD.",
    "Director de UCI": "Rigor clínico, datos HUN y seguridad.",
    "Investigador Científico": "Metodología, rigor y APA 7.",
    "Consultor Salud Digital": "BID/MinSalud y territorio.",
    "Professor Universitario": "Pedagogía médica disruptiva.",
    "Estratega de Trading": "Gestión de riesgo y SMC."
}

# --- 2. FUNCIONES DE LECTURA Y PERSISTENCIA NATIVA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])

DB_NATIVO = "memoria_nativa.json"
DATA_FOLDER = "biblioteca_master"

def actualizar_memoria_persistente():
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    biblioteca_data = []
    archivos_encontrados = 0
    for file in os.listdir(DATA_FOLDER):
        if file.lower().endswith(".pdf"):
            try:
                with open(os.path.join(DATA_FOLDER, file), "rb") as f:
                    texto = get_pdf_text(f)
                    if texto and texto.strip():
                        # Segmentación nativa: Chunks de 1200 caracteres con solapamiento
                        chunks = [texto[i:i+1200] for i in range(0, len(texto), 1000)]
                        for c in chunks:
                            biblioteca_data.append({"content": c, "source": file})
                        archivos_encontrados += 1
            except: continue
    if archivos_encontrados == 0: return "⚠️ No hay PDFs en 'biblioteca_master'."
    with open(DB_NATIVO, "w", encoding="utf-8") as f:
        json.dump(biblioteca_data, f, ensure_ascii=False)
    return f"✅ ÉXITO: {archivos_encontrados} documentos sincronizados."

def exportar_sesion():
    data = {"biblioteca": st.session_state.biblioteca, "messages": st.session_state.messages}
    return json.dumps(data, indent=4)

# --- 3. MOTOR DE EXPORTACIÓN ---
def clean_markdown(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    return text.strip()

def download_word_compilado(indices, messages):
    doc = docx.Document()
    for idx in sorted(indices):
        doc.add_paragraph(clean_markdown(messages[idx]["content"]))
        doc.add_page_break()
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_excel(content):
    try:
        lines = content.split('\n')
        table_data = [l.split('|') for l in lines if '|' in l]
        if len(table_data) > 1:
            df = pd.DataFrame(table_data[1:], columns=table_data[0])
            bio = BytesIO()
            with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return bio.getvalue()
    except: return None

# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "export_pool" not in st.session_state: st.session_state.export_pool = []
if "editor_version" not in st.session_state: st.session_state.editor_version = 0

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    if st.session_state.export_pool:
        st.divider()
        st.download_button("📄 Word Compilado", data=download_word_compilado(st.session_state.export_pool, st.session_state.messages), file_name=f"Reporte.docx", use_container_width=True)

    st.divider()
    tab_doc, tab_url = st.tabs(["📄 Sidebar", "🔗 URL"])
    with tab_doc:
        up = st.file_uploader("Análisis Volátil (Sidebar):", type=['pdf'], accept_multiple_files=True)
        if st.button("🧠 Procesar Sidebar", use_container_width=True):
            raw = "".join([get_pdf_text(f) for f in up])
            st.session_state.biblioteca[rol_activo] = raw[:40000]
            st.success("Cargado al Sidebar.")

    if st.session_state.biblioteca[rol_activo]:
        st.markdown("<div class='section-tag'>Curaduría</div>", unsafe_allow_html=True)
        nombre_c = st.text_input("Nombre para la Biblioteca:", value="Analisis_Vital.txt")
        if st.button("📌 Consagrar a Máster", use_container_width=True):
            with open(os.path.join(DATA_FOLDER, nombre_c), "w", encoding="utf-8") as f:
                f.write(st.session_state.biblioteca[rol_activo])
            actualizar_memoria_persistente()
            st.success("Guardado permanentemente.")

    st.divider()
    if st.button("🧠 Sincronizar Biblioteca Máster", use_container_width=True):
        st.info(actualizar_memoria_persistente())

# --- 6. PANEL CENTRAL: OMNI-VISION ---
ver = st.session_state.editor_version
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if st.checkbox("📥 Incluir", key=f"sel_{i}_{ver}", value=(i in st.session_state.export_pool)):
                if i not in st.session_state.export_pool: st.session_state.export_pool.append(i); st.rerun()
            elif i in st.session_state.export_pool: st.session_state.export_pool.remove(i); st.rerun()

if pr := st.chat_input("Nuestro reto hoy..."):
    fecha_actual = datetime.now().strftime("%d de %B de %Y")
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            # RAG NATIVO (Búsqueda en 10 fragmentos)
            contexto_rag = ""
            if os.path.exists(DB_NATIVO):
                with open(DB_NATIVO, "r", encoding="utf-8") as f:
                    data_master = json.load(f)
                palabras_clave = pr.lower().split()
                matches = []
                for item in data_master:
                    score = sum(2 for p in palabras_clave if p in item["content"].lower())
                    if score > 0: matches.append((score, item))
                matches.sort(key=lambda x: x[0], reverse=True)
                contexto_rag = "\n\n".join([f"--- FUENTE: {m[1]['source']} ---\n{m[1]['content']}" for m in matches[:10]])

            contexto_sidebar = st.session_state.biblioteca.get(rol_activo, "")
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            sys_prompt = f"""
            Actúa como {rol_activo}. ROI Cognitivo Prioritario.
            BIBLIOTECA MÁSTER: {contexto_rag[:18000]}
            SIDEBAR (ARTÍCULO): {contexto_sidebar[:18000]}
            
            ESTRUCTURA: ### Triage Estratégico, ### ROI Cognitivo, ### Análisis Multidimensional, ### Propuesta Táctica, **Pregunta de Punto Ciego**.
            REGLA: Si hay conflicto entre fuentes, señala '⚠️ ALERTA DE CHOQUE'. Cita siempre (Fuente: nombre_archivo.pdf).
            """
            
            resp = model.generate_content([sys_prompt, pr])
            st.markdown(resp.text)
            st.session_state.messages.append({"role": "assistant", "content": resp.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
