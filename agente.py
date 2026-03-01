import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import os
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from datetime import date
from pptx import Presentation

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="IkigAI V2.4 - Executive Hub", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("🔑 Configure su API Key."); st.stop()

# --- 2. MOTOR DE LECTURA REPARADO (Incluye TXT) ---
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

def sincronizar_maestra():
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    acumulado = []
    conteo = 0
    for file in os.listdir(DATA_FOLDER):
        txt = ""
        p = os.path.join(DATA_FOLDER, file)
        try:
            # EXTENSIÓN TXT AÑADIDA PARA ARCHIVOS CONSAGRADOS
            if file.lower().endswith(".pdf"):
                with open(p, "rb") as f: txt = get_pdf_text(f)
            elif file.lower().endswith(".docx"): txt = get_docx_text(p)
            elif file.lower().endswith(".pptx"): txt = get_pptx_text(p)
            elif file.lower().endswith(".txt"):
                with open(p, "r", encoding="utf-8") as f: txt = f.read()
            
            if txt:
                chunks = [txt[i:i+1500] for i in range(0, len(txt), 1200)]
                for ch in chunks: acumulado.append({"content": ch, "source": file})
                conteo += 1
        except Exception as e: continue
    
    with open(DB_JSON, "w", encoding="utf-8") as f:
        json.dump(acumulado, f, ensure_ascii=False)
    return f"✅ MEMORIA ACTUALIZADA: {conteo} archivos integrados (incluyendo consagrados)."

# --- 3. ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {r: "" for r in ["Coach de Alto Desempeño", "Director Centro Telemedicina", "Vicedecano Académico", "Director de UCI", "Investigador Científico", "Consultor Salud Digital", "Professor Universitario", "Estratega de Trading"]}
if "messages" not in st.session_state: st.session_state.messages = []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF;'>🧬</h1>", unsafe_allow_html=True)
    rol_activo = st.selectbox("ROL:", list(st.session_state.biblioteca.keys()))
    
    t_f, t_w, t_v = st.tabs(["📄 DOC", "🔗 URL", "🖼️ VIS"])
    with t_f:
        ups = st.file_uploader("Subir al Sidebar:", type=['pdf','docx','pptx'], accept_multiple_files=True)
        if st.button("🧠 Procesar Sidebar", use_container_width=True):
            raw = ""
            for f in ups:
                if f.name.endswith(".pdf"): raw += get_pdf_text(f)
                elif f.name.endswith(".docx"): raw += get_docx_text(f)
                elif f.name.endswith(".pptx"): raw += get_pptx_text(f)
            st.session_state.sidebar_content = raw[:50000]; st.success("Sidebar cargado.")

    # BOTÓN DE CONSAGRACIÓN CORREGIDO
    if "sidebar_content" in st.session_state and st.session_state.sidebar_content:
        st.divider()
        st.markdown("**📌 CURADURÍA DE ARCHIVO**")
        nombre_file = st.text_input("Nombre en Máster:", value=f"Curado_{date.today()}.txt")
        if st.button("📌 Consagrar a Máster", use_container_width=True):
            if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
            with open(os.path.join(DATA_FOLDER, nombre_file), "w", encoding="utf-8") as f:
                f.write(st.session_state.sidebar_content)
            # Sincronización inmediata post-consagración
            res = sincronizar_maestra()
            st.success(res)

    st.divider()
    if st.button("🧠 Sincronizar Todo", use_container_width=True):
        st.info(sincronizar_maestra())

# --- 5. PANEL CENTRAL ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if pr := st.chat_input("Consulta estratégica..."):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            # Búsqueda en Memoria Consolidada
            cr = ""
            if os.path.exists(DB_JSON):
                with open(DB_JSON, "r", encoding="utf-8") as f: master = json.load(f)
                matches = [it for it in master if any(p in it["content"].lower() for p in pr.lower().split())]
                cr = "\n\n".join([f"({x['source']}) {x['content']}" for x in matches[:10]])

            cs = st.session_state.get("sidebar_content", "")
            model = genai.GenerativeModel('gemini-2.5-flash')
            sys = f"Actúa como {rol_activo}. MÁSTER: {cr[:15000]}. SIDEBAR: {cs[:10000]}."
            resp = model.generate_content([sys, pr])
            st.markdown(resp.text)
            st.session_state.messages.append({"role": "assistant", "content": resp.text})
        except Exception as e: st.error(f"Error: {e}")
