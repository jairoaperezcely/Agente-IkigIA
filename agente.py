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

# --- 1. CONFIGURACIÓN E IDENTIDAD ZEN ---
st.set_page_config(page_title="IkigAI V2.3 - Executive Hub", page_icon="🧬", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    .stApp { background-color: #000000 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, h1, h2, h3 { color: #FFFFFF !important; }
    [data-testid="stChatMessage"] { background-color: #050505 !important; border: 1px solid #1A1A1A !important; border-radius: 10px; }
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    .stDownloadButton button, .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; box-shadow: 0 0 15px rgba(0, 230, 255, 0.4); }
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
    "Director Centro Telemedicina": "Enfoque en transformación digital e interoperabilidad UNAL.",
    "Vicedecano Académico": "Gestión académica, normativa y estándares MD-PhD.",
    "Director de UCI": "Rigor clínico, seguridad del paciente y datos HUN.",
    "Investigador Científico": "Metodología traslacional y rigor APA 7.",
    "Consultor Salud Digital": "Sostenibilidad BID/MinSalud e impacto territorial.",
    "Professor Universitario": "Pedagogía médica disruptiva.",
    "Estratega de Trading": "Gestión de riesgo (RR) y confluencias SMC."
}

# --- 2. LECTORES ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages if p.extract_text()])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_pptx_text(f):
    prs = Presentation(f); t = []
    for s in prs.slides:
        for sh in s.shapes:
            if hasattr(sh, "text"): t.append(sh.text)
    return "\n".join(t)

DB_JSON = "memoria_nativa.json"
DATA_FOLDER = "biblioteca_master"

def sincronizar():
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    acumulado = []
    c = 0
    for file in os.listdir(DATA_FOLDER):
        txt = ""
        p = os.path.join(DATA_FOLDER, file)
        try:
            if file.lower().endswith(".pdf"):
                with open(p, "rb") as f: txt = get_pdf_text(f)
            elif file.lower().endswith(".docx"): txt = get_docx_text(p)
            elif file.lower().endswith(".pptx"): txt = get_pptx_text(p)
            if txt:
                chunks = [txt[i:i+1200] for i in range(0, len(txt), 1000)]
                for ch in chunks: acumulado.append({"content": ch, "source": file})
                c += 1
        except: continue
    with open(DB_JSON, "w", encoding="utf-8") as f: json.dump(acumulado, f, ensure_ascii=False)
    return f"✅ ÉXITO: {c} documentos sincronizados."

# --- 3. ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {r: "" for r in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "export_pool" not in st.session_state: st.session_state.export_pool = []

# --- 4. BARRA LATERAL (RESTAURADA) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF;'>🧬</h1>", unsafe_allow_html=True)
    rol_activo = st.radio("ROL ACTIVO:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    st.divider()
    t_f, t_w, t_v = st.tabs(["📄 DOC", "🔗 URL", "🖼️ VIS"])
    
    with t_f:
        ups = st.file_uploader("Subir archivos (Sidebar):", type=['pdf','docx','pptx'], accept_multiple_files=True)
        if st.button("🧠 Procesar Sidebar", use_container_width=True):
            raw = ""
            for f in ups:
                if f.name.endswith(".pdf"): raw += get_pdf_text(f)
                elif f.name.endswith(".docx"): raw += get_docx_text(f)
                elif f.name.endswith(".pptx"): raw += get_pptx_text(f)
            st.session_state.biblioteca[rol_activo] = raw[:40000]; st.success("Sidebar listo.")

    # --- NODO DE CONSAGRACIÓN (EL BOTÓN FALTANTE) ---
    if st.session_state.biblioteca[rol_activo]:
        st.markdown("<div class='section-tag'>CURADURÍA ACTIVA</div>", unsafe_allow_html=True)
        nombre_consagrado = st.text_input("Nombre para la Máster:", value=f"Articulo_{date.today()}.txt")
        if st.button("📌 Consagrar a Biblioteca Máster", use_container_width=True):
            if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
            ruta_final = os.path.join(DATA_FOLDER, nombre_consagrado)
            with open(ruta_final, "w", encoding="utf-8") as f:
                f.write(st.session_state.biblioteca[rol_activo])
            sincronizar() # Sincroniza automáticamente al guardar
            st.success(f"Blindado en Máster como {nombre_consagrado}")

    with t_w:
        u = st.text_input("URL:")
        if st.button("🌐 Scrapear", use_container_width=True):
            try:
                r = requests.get(u, timeout=10)
                st.session_state.biblioteca[rol_activo] = BeautifulSoup(r.text, 'html.parser').get_text()[:30000]; st.success("Web lista.")
            except: st.error("Error URL.")

    with t_v:
        img_f = st.file_uploader("Imagen:", type=['jpg','png','jpeg'])
        if img_f and st.button("👁️ Analizar", use_container_width=True):
            img = Image.open(img_f)
            mv = genai.GenerativeModel('gemini-2.5-flash')
            rv = mv.generate_content(["Análisis estratégico de imagen:", img])
            st.session_state.biblioteca[rol_activo] = rv.text; st.success("Imagen procesada.")

    st.divider()
    if st.button("🧠 Sincronizar Biblioteca Máster", use_container_width=True):
        st.info(sincronizar())

# --- 5. PANEL CENTRAL (OMNI-VISION) ---
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if pr := st.chat_input("Nuestro reto hoy..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            cr = ""
            if os.path.exists(DB_JSON):
                with open(DB_JSON, "r", encoding="utf-8") as f: master = json.load(f)
                pal = pr.lower().split()
                m = []
                for it in master:
                    sc = sum(2 for p in pal if p in it["content"].lower())
                    if sc > 0: m.append((sc, it))
                m.sort(key=lambda x: x[0], reverse=True)
                cr = "\n\n".join([f"(Fuente: {x[1]['source']}) {x[1]['content']}" for x in m[:10]])

            cs = st.session_state.biblioteca.get(rol_activo, "")
            model = genai.GenerativeModel('gemini-2.5-flash')
            sys = f"Actúa como {rol_activo}. MÁSTER: {cr[:15000]}. SIDEBAR: {cs[:15000]}."
            resp = model.generate_content([sys, pr])
            st.markdown(resp.text)
            st.session_state.messages.append({"role": "assistant", "content": resp.text}); st.rerun()
        except Exception as e: st.error(f"Error motor: {e}")
