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

# --- LIBRERÍAS DE OFICINA & GRÁFICOS ---
from pptx import Presentation
import matplotlib.pyplot as plt
import pandas as pd

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
st.set_page_config(page_title="Agente V14 (Omnívoro)", page_icon="🧬", layout="wide")

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# FUNCIONES DE LECTURA (INPUT)
# ==========================================

def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# NUEVO: LEER EXCEL
def get_excel_text(excel_file):
    try:
        # Lee todas las hojas del Excel
        all_sheets = pd.read_excel(excel_file, sheet_name=None)
        text = ""
        for sheet_name, df in all_sheets.items():
            text += f"\n--- HOJA: {sheet_name} ---\n"
            text += df.to_string() # Convierte la tabla a texto legible
        return text
    except Exception as e: return f"Error leyendo Excel: {e}"

# NUEVO: LEER POWERPOINT
def get_pptx_text(pptx_file):
    try:
        prs = Presentation(pptx_file)
        text = ""
        for i, slide in enumerate(prs.slides):
            text += f"\n--- DIAPOSITIVA {i+1} ---\n"
            # Extraer texto de todas las formas (títulos, cuadros de texto)
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text
    except Exception as e: return f"Error leyendo PPTX: {e}"

# ==========================================
# FUNCIONES DE GENERACIÓN (OUTPUT)
# ==========================================

# 1. WORD ACTA
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading(f'Acta: {date.today().strftime("%d/%m/%Y")}', 0)
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "IA"
        doc.add_heading(role, level=2)
        doc.add_paragraph(msg["content"])
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 2. WORD LIMPIO
def create_clean_docx(text_content):
    doc = docx.Document()
    clean_text = text_content.replace("```markdown", "").replace("```", "")
    for paragraph in clean_text.split('\n'):
        if paragraph.strip(): doc.add_paragraph(paragraph)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 3. PPTX
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

# 4. EXCEL
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, index=False, sheet_name=sheet_name[:30])
    output.seek(0)
    return output

# 5. GRÁFICO
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

# FUNCIONES WEB/YT
def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "YT: " + " ".join([i['text'] for i in t])
    except: return "Error YT"

def get_web_text(url):
    try: return "WEB: " + "\n".join([p.get_text() for p in BeautifulSoup(requests.get(url).content, 'html.parser').find_all('p')])
    except: return "Error Web"

# ==========================================
# ESTADO
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
if "info_archivos" not in st.session_state: st.session_state.info_archivos = "Ninguno"
# Outputs
if "generated_pptx" not in st.session_state: st.session_state.generated_pptx = None
if "generated_chart" not in st.session_state: st.session_state.generated_chart = None
if "generated_excel" not in st.session_state: st.session_state.generated_excel = None
if "generated_word_clean" not in st.session_state: st.session_state.generated_word_clean = None

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2)
    st.divider()
    rol = st.radio("Rol:", ["Vicedecano Académico", "Director de UCI", "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", "Mentor de Trading", "Asistente Personal"])
    
    prompts_roles = {
        "Vicedecano Académico": "Eres Vicedecano. Riguroso, normativo y formal.",
        "Director de UCI": "Eres Médico Intensivista. Prioriza guías clínicas y seguridad.",
        "Consultor Telesalud": "Eres experto en Salud Digital y Leyes.",
        "Profesor Universitario": "Eres docente. Explica con pedagogía.",
        "Investigador Científico": "Eres metodólogo. Prioriza datos y referencias.",
        "Mentor de Trading": "Eres Trader Institucional. Analiza estructura y liquidez.",
        "Asistente Personal": "Eres asistente ejecutivo eficiente."
    }

    st.subheader("🛠️ GENERADOR")
    # 1. WORD
    if st.button("📄 Word (Doc)"):
        if st.session_state.messages:
            st.session_state.generated_word_clean = create_clean_docx(st.session_state.messages[-1]["content"])
            st.success("✅ Doc Listo")
    if st.session_state.generated_word_clean: st.download_button("📥 Bajar Doc", st.session_state.generated_word_clean, "doc.docx")

    # 2. PPTX
    if st.button("🗣️ PPTX"):
        with st.spinner("Creando PPTX..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
            prompt = f"Analiza: {hist}. JSON PPTX: [{{'title':'T','content':['A']}}]"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                st.session_state.generated_pptx = generate_pptx_from_data(json.loads(res.text.replace("```json","").replace("```","").strip()))
                st.success("✅ PPTX Listo")
            except: st.error("Error PPTX")
    if st.session_state.generated_pptx: st.download_button("📥 Bajar PPTX", st.session_state.generated_pptx, "pres.pptx")

    # 3. EXCEL
    if st.button("x ̅  Excel"):
        with st.spinner("Creando Excel..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Analiza: {hist}. JSON Excel: {{'Hoja1': [{{'ColA':'Val1'}}]}}"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                st.session_state.generated_excel = generate_excel_from_data(json.loads(res.text.replace("```json","").replace("```","").strip()))
                st.success("✅ Excel Listo")
            except Exception as e: st.error(f"Error Excel: {e}")
    if st.session_state.generated_excel: st.download_button("📥 Bajar Excel", st.session_state.generated_excel, "data.xlsx")

    # 4. GRÁFICO
    if st.button("📊 Gráfico"):
        with st.spinner("Graficando..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Datos de: {hist}. JSON: {{'title':'T','labels':['A'],'datasets':[{{'label':'L','values':[1],'type':'bar'}}]}}"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                st.session_state.generated_chart = generate_advanced_chart(json.loads(res.text.replace("```json","").replace("```","").strip()))
                st.success("✅ Gráfico Listo")
            except: st.error("No hay datos")

    st.divider()
    # GESTIÓN Y CARGA MASIVA
    st.subheader("📥 FUENTES UNIVERSALES")
    tab1, tab2, tab3, tab4 = st.tabs(["📂 Docs", "👁️ Media", "🔴 YT", "🌐 Web"])
    
    with tab1:
        # AQUI ESTÁ EL CAMBIO IMPORTANTE: ACEPTA PDF, DOCX, XLSX, PPTX
        uploaded_docs = st.file_uploader("Subir Archivos", type=['pdf', 'docx', 'xlsx', 'pptx'], accept_multiple_files=True)
        if uploaded_docs and st.button(f"Leer {len(uploaded_docs)} Archivos"):
            text_acc = ""
            prog = st.progress(0)
            for i, doc in enumerate(uploaded_docs):
                try:
                    if doc.type == "application/pdf": 
                        text_acc += f"\n--- PDF: {doc.name} ---\n{get_pdf_text(doc)}"
                    elif doc.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        text_acc += f"\n--- WORD: {doc.name} ---\n{get_docx_text(doc)}"
                    elif doc.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                        text_acc += f"\n--- EXCEL: {doc.name} ---\n{get_excel_text(doc)}"
                    elif doc.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                        text_acc += f"\n--- PPTX: {doc.name} ---\n{get_pptx_text(doc)}"
                except Exception as e: st.error(f"Error en {doc.name}: {e}")
                prog.progress((i+1)/len(uploaded_docs))
            st.session_state.contexto_texto = text_acc
            st.session_state.info_archivos = f"{len(uploaded_docs)} archivos cargados."
            st.success("✅ Biblioteca Cargada")
    
    with tab2:
        uploaded_media = st.file_uploader("Media", type=['mp4','mp3','png','jpg'])
        if uploaded_media and api_key and st.button("Subir Media"):
            genai.configure(api_key=api_key)
            with st.spinner("Procesando..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.'+uploaded_media.name.split('.')[-1]) as tf:
                    tf.write(uploaded_media.read()); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
                st.session_state.archivo_multimodal = mfile
                st.success("✅ Media Lista"); os.remove(tpath)
    with tab3:
        if st.button("YT") and (u:=st.text_input("Link YT")): st.session_state.contexto_texto=get_youtube_text(u);st.success("✅ YT")
    with tab4:
        if st.button("Web") and (w:=st.text_input("Link Web")): st.session_state.contexto_texto=get_web_text(w);st.success("✅ Web")

    st.divider()
    if st.session_state.messages:
        st.download_button("💾 Guardar Chat", create_chat_docx(st.session_state.messages), "chat.docx")
        st.download_button("🧠 Backup JSON", json.dumps(st.session_state.messages), "memoria.json")
    if st.file_uploader("Cargar Backup", type=['json']) and st.button("Restaurar"): st.session_state.messages = json.load(uploaded_memory); st.rerun()
    if st.button("🗑️ Borrar"): st.session_state.clear(); st.rerun()

# ==========================================
# CHAT
# ==========================================
st.title(f"🤖 Agente V14: {rol}")
if not api_key: st.warning("⚠️ API Key requerida"); st.stop()
if st.session_state.generated_chart: st.pyplot(st.session_state.generated_chart); st.button("Cerrar Gráfico", on_click=lambda: st.session_state.update(generated_chart=None))

genai.configure(api_key=api_key)
model = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": temp_val})

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Instrucción..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        with st.spinner("..."):
            ctx = st.session_state.contexto_texto
            prompt = f"Rol: {rol}. {('Usa SOLO adjuntos.' if ctx else 'Usa conocimiento general.')} Historial: {st.session_state.messages[-5:]}. Consulta: {p}"
            if ctx: prompt += f"\nDOCS: {ctx[:500000]}"
            if st.session_state.archivo_multimodal: prompt += " (Analiza el archivo multimedia adjunto)."
            
            # Manejo de adjuntos multimedia en la llamada
            con = [prompt]
            if st.session_state.archivo_multimodal: con.insert(0, st.session_state.archivo_multimodal)
            
            res = model.generate_content(con)
            st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
