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
# LIBRERÍAS DE OFICINA
from pptx import Presentation
import matplotlib.pyplot as plt
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente IkigAI", page_icon="💼", layout="wide")

# --- FUNCIONES DE LECTURA ---
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- 1. GENERAR WORD (ACTA - HISTORIAL) ---
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading(f'Acta: {date.today().strftime("%d/%m/%Y")}', 0)
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "IA"
        doc.add_heading(role, level=2)
        doc.add_paragraph(msg["content"])
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- 2. GENERAR WORD (LIMPIO - DOCUMENTO) ---
def create_clean_docx(text_content):
    doc = docx.Document()
    # Limpiamos posibles bloques de código markdown
    clean_text = text_content.replace("```markdown", "").replace("```", "")
    for paragraph in clean_text.split('\n'):
        if paragraph.strip(): 
            doc.add_paragraph(paragraph)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- 3. GENERAR PPTX ---
def generate_pptx_from_data(slide_data):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = slide_data[0].get("title", "Presentación IA")
    slide.placeholders[1].text = f"Fecha: {date.today()}"
    for info in slide_data[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = info.get("title", "Título")
        tf = slide.placeholders[1].text_frame
        for point in info.get("content", []):
            p = tf.add_paragraph(); p.text = point; p.level = 0
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

# --- 4. GENERAR EXCEL ---
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, index=False, sheet_name=sheet_name[:30])
    output.seek(0)
    return output

# --- 5. GENERAR GRÁFICO ---
def generate_advanced_chart(chart_data):
    fig, ax = plt.subplots(figsize=(10, 5))
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = chart_data.get("labels", [])
    for ds in chart_data.get("datasets", []):
        if len(ds["values"]) == len(labels):
            if ds.get("type") == "line": ax.plot(labels, ds["values"], label=ds["label"], marker='o')
            else: ax.bar(labels, ds["values"], label=ds["label"], alpha=0.6)
    ax.legend(); ax.set_title(chart_data.get("title", "Gráfico")); plt.tight_layout()
    return fig

# --- FUNCIONES WEB/YT ---
def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "YT: " + " ".join([i['text'] for i in t])
    except: return "Error YT"

def get_web_text(url):
    try: return "WEB: " + "\n".join([p.get_text() for p in BeautifulSoup(requests.get(url).content, 'html.parser').find_all('p')])
    except: return "Error Web"

# --- ESTADO ---
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
# Estados para descargas
if "generated_pptx" not in st.session_state: st.session_state.generated_pptx = None
if "generated_chart" not in st.session_state: st.session_state.generated_chart = None
if "generated_excel" not in st.session_state: st.session_state.generated_excel = None
if "generated_word_clean" not in st.session_state: st.session_state.generated_word_clean = None

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp = st.slider("Creatividad", 0.0, 1.0, 0.2)
    st.divider()
    rol = st.radio("Rol:", ["Vicedecano Académico", "Director de UCI", "Consultor telesalud", "Profesor Universitario", "Investigador", "Mentor de Trading", "Asistente personal"])
    
    # --- HERRAMIENTAS DE SALIDA ---
    st.subheader("🛠️ GENERADOR DE ARCHIVOS")
    
    # 1. DOC LIMPIO (NUEVO)
    if st.button("📄 Word"):
        if not st.session_state.messages: st.error("No hay respuesta para descargar.")
        else:
            last_msg = st.session_state.messages[-1]["content"]
            st.session_state.generated_word_clean = create_clean_docx(last_msg)
            st.success("✅ Doc Listo")
    if st.session_state.generated_word_clean:
        st.download_button("📥 Bajar Documento.docx", st.session_state.generated_word_clean, "documento_ia.docx")

    # 2. PPTX
    if st.button("🗣️ PPTX"):
        with st.spinner("Creando PPTX..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
            prompt = f"Crea JSON para PPTX basado en: {hist}. Formato: [{{'title':'T','content':['A']}}]"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel('gemini-2.5-flash')
                res = mod.generate_content(prompt)
                st.session_state.generated_pptx = generate_pptx_from_data(json.loads(res.text.replace("```json","").replace("```","")))
                st.success("✅ PPTX Listo")
            except: st.error("Error PPTX")
    if st.session_state.generated_pptx: st.download_button("📥 Bajar PPTX", st.session_state.generated_pptx, "presentacion.pptx")

    # 3. EXCEL
    if st.button("xlx Excel"):
        if len(st.session_state.messages) < 2: st.error("Faltan datos.")
        else:
            with st.spinner("Creando Excel..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt_excel = f"""Analiza: {hist}. Genera JSON para Excel. Si es encuesta, columnas Pregunta/Tipo. Si son datos, sus columnas. JSON: {{'Hoja1': [{{'ColA':'Val1'}}]}}"""
                try:
                    genai.configure(api_key=api_key); mod = genai.GenerativeModel('gemini-2.5-flash')
                    res = mod.generate_content(prompt_excel)
                    st.session_state.generated_excel = generate_excel_from_data(json.loads(res.text.replace("```json","").replace("```","")))
                    st.success("✅ Excel Listo")
                except: st.error("Error Excel")
    if st.session_state.generated_excel: st.download_button("📥 Bajar Excel.xlsx", st.session_state.generated_excel, "datos.xlsx")

    # 4. GRÁFICO
    if st.button("📊 Generar Gráfico"):
        with st.spinner("Graficando..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Extrae datos de: {hist}. JSON: {{'title':'T','labels':['A'],'datasets':[{{'label':'L','values':[1],'type':'bar'}}]}}"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel('gemini-2.5-flash')
                res = mod.generate_content(prompt)
                st.session_state.generated_chart = generate_advanced_chart(json.loads(res.text.replace("```json","").replace("```","")))
                st.success("✅ Gráfico Listo")
            except: st.error("No hay datos claros.")

    st.divider()
    # GESTIÓN (Acta Completa / Backup)
    if st.session_state.messages: 
        st.download_button("💾 Acta Completa (Chat)", create_chat_docx(st.session_state.messages), "historial_chat.docx")
        st.download_button("🧠 Backup Memoria", json.dumps(st.session_state.messages), "cerebro.json")
    if st.button("🗑️ Nueva Sesión"): st.session_state.clear(); st.rerun()

# --- CHAT ---
st.title(f"🤖 Agente IkigAI: {rol}")
if st.session_state.generated_chart: st.pyplot(st.session_state.generated_chart); st.button("Cerrar Gráfico", on_click=lambda: st.session_state.update(generated_chart=None))

if not api_key: st.warning("⚠️ Ingrese API Key"); st.stop()
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"temperature": temp})

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Escriba aquí..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            ctx = st.session_state.contexto_texto
            prompt = f"Rol: {rol}. {('Usa SOLO adjuntos.' if ctx else 'Usa conocimiento general.')} Historial: {st.session_state.messages[-5:]}. Pregunta: {p}"
            if ctx: prompt += f"\nDOC: {ctx[:500000]}"
            res = model.generate_content(prompt)
            st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()

