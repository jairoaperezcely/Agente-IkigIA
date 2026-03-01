import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import pandas as pd
import os
import re
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from datetime import date, datetime
from pptx import Presentation
from pptx.util import Inches, Pt

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL (ESTRUCTURA BLINDADA) ---
st.set_page_config(
    page_title="IkigAI V2.7 - Executive Workstation", 
    page_icon="🧬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profesional para mantener el Sidebar organizado
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; min-width: 360px !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, h1, h2, h3 { color: #FFFFFF !important; }
    [data-testid="stChatMessage"] { background-color: #050505 !important; border: 1px solid #1A1A1A !important; border-radius: 10px; margin-bottom: 15px; }
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; height: 42px; margin-top: 10px; }
    .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; box-shadow: 0 0 15px rgba(0, 230, 255, 0.4); }
    .section-tag { font-size: 11px; color: #00E6FF; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid #1A1A1A; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Error: Falta API Key."); st.stop()

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

# --- 2. MOTORES DE LECTURA (RESTAURADOS) ---
def get_pdf_text(f):
    reader = PdfReader(f)
    return "".join([p.extract_text() for p in reader.pages if p.extract_text()])

def get_docx_text(f):
    doc = docx.Document(f)
    return "\n".join([p.text for p in doc.paragraphs])

def get_pptx_text(f):
    prs = Presentation(f); text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"): text.append(shape.text)
    return "\n".join(text)

DB_JSON = "memoria_nativa.json"
DATA_FOLDER = "biblioteca_master"

def sincronizar_total():
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    acumulado = []
    c = 0
    for file in os.listdir(DATA_FOLDER):
        txt = ""
        p = os.path.join(DATA_FOLDER, file)
        try:
            ext = file.lower()
            if ext.endswith(".pdf"):
                with open(p, "rb") as f: txt = get_pdf_text(f)
            elif ext.endswith(".docx"): txt = get_docx_text(p)
            elif ext.endswith(".pptx"): txt = get_pptx_text(p)
            elif ext.endswith(".txt"):
                with open(p, "r", encoding="utf-8") as f: txt = f.read()
            
            if txt:
                # Segmentación estratégica
                chunks = [txt[i:i+1500] for i in range(0, len(txt), 1200)]
                for ch in chunks: acumulado.append({"content": ch, "source": file})
                c += 1
        except: continue
    with open(DB_JSON, "w", encoding="utf-8") as f:
        json.dump(acumulado, f, ensure_ascii=False)
    return f"✅ Memoria Sincronizada: {c} archivos detectados."

# --- 3. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {r: "" for r in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "sidebar_content" not in st.session_state: st.session_state.sidebar_content = ""

# --- 4. BARRA LATERAL (CONTROL TOTAL) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF;'>🧬</h1>", unsafe_allow_html=True)
    rol_activo = st.selectbox("IDENTIDAD ACTIVA:", list(ROLES.keys()))
    
    st.markdown("<div class='section-tag'>ENTRADA DE DATOS</div>", unsafe_allow_html=True)
    t_doc, t_url, t_vis = st.tabs(["📄 DOC", "🔗 URL", "🖼️ VIS"])
    
    with t_doc:
        ups = st.file_uploader("Cargar PDF/DOCX/PPTX:", type=['pdf','docx','pptx'], accept_multiple_files=True)
        if st.button("🧠 PROCESAR SIDEBAR"):
            raw = ""
            for f in ups:
                if f.name.endswith(".pdf"): raw += get_pdf_text(f)
                elif f.name.endswith(".docx"): raw += get_docx_text(f)
                elif f.name.endswith(".pptx"): raw += get_pptx_text(f)
            st.session_state.sidebar_content = raw[:50000]; st.success("Sidebar listo.")

    with t_url:
        u_in = st.text_input("Pegar URL:")
        if st.button("🌐 SCRAPEAR WEB"):
            try:
                r = requests.get(u_in, timeout=10)
                st.session_state.sidebar_content = BeautifulSoup(r.text, 'html.parser').get_text()[:30000]
                st.success("Web integrada.")
            except: st.error("URL no válida.")

    with t_vis:
        img_f = st.file_uploader("Subir imagen:", type=['jpg','png','jpeg'])
        if img_f and st.button("👁️ VISIÓN AI"):
            img = Image.open(img_f)
            m_v = genai.GenerativeModel('gemini-2.5-flash')
            res_v = m_v.generate_content(["Analiza esta imagen para mi rol:", img])
            st.session_state.sidebar_content = res_v.text; st.success("Imagen analizada.")

    # --- BOTÓN DE CONSAGRACIÓN (RESTAURADO) ---
    if st.session_state.sidebar_content:
        st.markdown("<div class='section-tag'>CURADURÍA</div>", unsafe_allow_html=True)
        nombre_f = st.text_input("Nombre en Máster:", value=f"Dato_{date.today().strftime('%d_%m')}.txt")
        if st.button("📌 CONSAGRAR A MÁSTER"):
            if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
            with open(os.path.join(DATA_FOLDER, nombre_f), "w", encoding="utf-8") as f:
                f.write(st.session_state.sidebar_content)
            sincronizar_total() # Sincronización automática
            st.success(f"Archivo {nombre_f} blindado.")

    st.markdown("<div class='section-tag'>SISTEMA</div>", unsafe_allow_html=True)
    if st.button("🧠 SINCRONIZAR TODO"):
        st.info(sincronizar_total())

# --- 5. PANEL CENTRAL (OMNI-VISION) ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if pr := st.chat_input("Consulta estratégica..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            # Búsqueda RAG en 10 fragmentos
            cr = ""
            if os.path.exists(DB_JSON):
                with open(DB_JSON, "r", encoding="utf-8") as f: master = json.load(f)
                pal = pr.lower().split()
                matches = [it for it in master if any(p in it["content"].lower() for p in pal)]
                matches.sort(key=lambda x: sum(1 for p in pal if p in x["content"].lower()), reverse=True)
                cr = "\n\n".join([f"(Fuente: {x['source']}) {x['content']}" for x in matches[:10]])

            cs = st.session_state.sidebar_content
            model = genai.GenerativeModel('gemini-2.5-flash')
            sys = f"Actúa como {rol_activo}. MÁSTER: {cr[:15000]}. SIDEBAR: {cs[:10000]}. Cita siempre fuentes."
            resp = model.generate_content([sys, pr])
            st.markdown(resp.text)
            st.session_state.messages.append({"role": "assistant", "content": resp.text}); st.rerun()
        except Exception as e: st.error(f"Error: {e}")
