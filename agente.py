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
st.set_page_config(page_title="IkigAI V1.95 - Total Vision", page_icon="🧬", layout="wide")

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

# --- 2. MOTOR MULTIFORMATO Y WEB ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_pptx_text(f):
    prs = Presentation(f); text = []
    for s in prs.slides:
        for sh in s.shapes:
            if hasattr(sh, "text"): text.append(sh.text)
    return "\n".join(text)

DB_NATIVO = "memoria_nativa.json"
DATA_FOLDER = "biblioteca_master"

def actualizar_memoria_persistente():
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    biblioteca_data = []
    archivos_encontrados = 0
    for file in os.listdir(DATA_FOLDER):
        texto = ""
        try:
            path = os.path.join(DATA_FOLDER, file)
            if file.lower().endswith(".pdf"): texto = get_pdf_text(open(path, "rb"))
            elif file.lower().endswith(".docx"): texto = get_docx_text(path)
            elif file.lower().endswith(".pptx"): texto = get_pptx_text(path)
            if texto:
                chunks = [texto[i:i+1200] for i in range(0, len(texto), 1000)]
                for c in chunks: biblioteca_data.append({"content": c, "source": file})
                archivos_encontrados += 1
        except: continue
    with open(DB_NATIVO, "w", encoding="utf-8") as f: json.dump(biblioteca_data, f, ensure_ascii=False)
    return f"✅ ÉXITO: {archivos_encontrados} documentos sincronizados."

# --- 3. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "export_pool" not in st.session_state: st.session_state.export_pool = []

# --- 4. BARRA LATERAL (MULTIFUENTE) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF;'>🧬</h1>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    st.divider()
    t_doc, t_url, t_img = st.tabs(["📄 DOC", "🔗 URL", "🖼️ IMG"])
    
    with t_doc:
        up = st.file_uploader("Subir PDF/DOCX/PPTX:", type=['pdf', 'docx', 'pptx'], accept_multiple_files=True)
        if st.button("🧠 Procesar Sidebar", use_container_width=True):
            raw = ""
            for f in up:
                if f.name.endswith(".pdf"): raw += get_pdf_text(f)
                elif f.name.endswith(".docx"): raw += get_docx_text(f)
                elif f.name.endswith(".pptx"): raw += get_pptx_text(f)
            st.session_state.biblioteca[rol_activo] = raw[:40000]; st.success("Sidebar listo.")

    with t_url:
        url_in = st.text_input("URL:")
        if st.button("🌐 Scrapear Web", use_container_width=True):
            try:
                res = requests.get(url_in)
                soup = BeautifulSoup(res.text, 'html.parser')
                st.session_state.biblioteca[rol_activo] = soup.get_text()[:30000]; st.success("Web integrada.")
            except: st.error("URL inaccesible.")

    with t_img:
        up_i = st.file_uploader("Imagen:", type=['jpg', 'png', 'jpeg'])
        if up_i and st.button("👁️ Visión AI", use_container_width=True):
            img = Image.open(up_i)
            m_v = genai.GenerativeModel('gemini-1.5-flash')
            res_v = m_v.generate_content(["Analiza esta imagen para contexto estratégico:", img])
            st.session_state.biblioteca[rol_activo] = res_v.text; st.success("Imagen analizada.")

    if st.button("🧠 Sincronizar Biblioteca Máster", use_container_width=True):
        st.info(actualizar_memoria_persistente())

# --- 5. PANEL CENTRAL ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and st.checkbox("📥 Incluir", key=f"s_{i}"):
            if i not in st.session_state.export_pool: st.session_state.export_pool.append(i); st.rerun()

if pr := st.chat_input("Nuestro reto hoy..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            # RAG OMNI (10 Fragmentos)
            c_rag = ""
            if os.path.exists(DB_NATIVO):
                with open(DB_NATIVO, "r", encoding="utf-8") as f:
                    master = json.load(f)
                keys = pr.lower().split()
                m = []
                for it in master:
                    sc = sum(2 for k in keys if k in it["content"].lower())
                    if sc > 0: m.append((sc, it))
                m.sort(key=lambda x: x[0], reverse=True)
                c_rag = "\n\n".join([f"(Fuente: {x[1]['source']}) {x[1]['content']}" for x in m[:10]])

            c_sid = st.session_state.biblioteca.get(rol_activo, "")
            model = genai.GenerativeModel('gemini-1.5-flash') # Gemini 1.5 para mayor estabilidad multiformato
            sys = f"Actúa como {rol_activo}. MÁSTER: {c_rag[:15000]}. SIDEBAR: {c_sid[:15000]}. Prioriza Triage y ROI."
            resp = model.generate_content([sys, pr])
            st.markdown(resp.text)
            st.session_state.messages.append({"role": "assistant", "content": resp.text})
            st.rerun()
        except Exception as e: st.error(f"Error: {e}")
