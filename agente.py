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
# --- NUEVAS LIBRERÍAS V11.0 ---
from pptx import Presentation
from pptx.util import Inches, Pt
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente V11.0 (Constructor PPTX/Gráficos)", page_icon="🧬", layout="wide")

# --- FUNCIONES DE LECTURA DE TEXTO ---
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- FUNCIÓN GENERAR WORD (ACTA) ---
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading(f'Acta de Sesión: {date.today().strftime("%d/%m/%Y")}', 0)
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "ASISTENTE IA"
        doc.add_heading(role, level=2)
        doc.add_paragraph(msg["content"])
        doc.add_paragraph("---")
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- NUEVA FUNCIÓN: GENERAR POWERPOINT (PPTX) ---
def generate_pptx_from_data(slide_data):
    """Crea un PPTX basado en una lista de datos estructurados."""
    prs = Presentation()
    
    # Diapositiva de Título
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = slide_data[0].get("title", "Presentación Generada por IA")
    subtitle.text = f"Fecha: {date.today().strftime('%d/%m/%Y')}"

    # Diapositivas de Contenido
    bullet_slide_layout = prs.slide_layouts[1]
    for slide_info in slide_data[1:]:
        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        
        title_shape.text = slide_info.get("title", "Título")
        tf = body_shape.text_frame
        
        content_list = slide_info.get("content", [])
        if content_list:
            tf.text = content_list[0] # Primer punto
            for point in content_list[1:]:
                p = tf.add_paragraph()
                p.text = point
                p.level = 0 # Nivel de viñeta

    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer

# --- NUEVA FUNCIÓN: GENERAR GRÁFICO (MATPLOTLIB) ---
def generate_chart_from_data(chart_data):
    """Genera un gráfico de barras simple desde datos JSON."""
    labels = chart_data.get("labels", [])
    values = chart_data.get("values", [])
    title = chart_data.get("title", "Gráfico de Datos")

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(labels, values, color='#4A90E2')
    
    ax.set_ylabel('Valor')
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    
    # Añadir valores sobre las barras
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    plt.tight_layout()
    return fig

# --- FUNCIONES WEB Y YOUTUBE ---
def get_youtube_text(video_url):
    try:
        if "v=" in video_url: video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be" in video_url: video_id = video_url.split("/")[-1]
        else: return "URL inválida."
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        text = " ".join([entry['text'] for entry in transcript])
        return f"TRANSCRIPCIÓN YOUTUBE:\n{text}"
    except: return "No se pudo obtener la transcripción."

def get_web_text(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        text = "\n".join([p.get_text() for p in soup.find_all('p')])
        return f"CONTENIDO WEB ({url}):\n{text}"
    except Exception as e: return f"Error web: {str(e)}"

# --- ESTADO ---
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
if "info_archivos" not in st.session_state: st.session_state.info_archivos = "Ninguno"
if "generated_pptx" not in st.session_state: st.session_state.generated_pptx = None
if "generated_chart" not in st.session_state: st.session_state.generated_chart = None

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    
    st.caption("Creatividad (0=Preciso | 1=Libre):")
    temp_val = st.slider("", 0.0, 1.0, 0.2, 0.1)
    
    st.divider()
    
    rol = st.radio("Perfil Activo:", ["Vicedecano Académico", "Director de UCI", "Experto en Telesalud", "Investigador Científico", "Profesor universitario", "Asistente Personal", "Mentor de Trading"])
    
    prompts_roles = {
        "Vicedecano Académico": "Eres Vicedecano riguroso. Cita normativas.",
        "Director de UCI": "Eres Director de UCI. Prioriza seguridad del paciente.",
        "Mentor de Trading": "Eres Trader Institucional (Smart Money). Analiza estructura y riesgo.",
        "Experto en Telesalud": "Eres experto en Salud Digital y normativa.",
        "Investigador Científico": "Eres metodólogo. Prioriza validez estadística.",
        "Profesor universitario": "Eres docente socrático. Explica con claridad.",
        "Asistente Personal": "Eres asistente ejecutivo eficiente."
    }

    st.divider()
    
    # --- NUEVA SECCIÓN: HERRAMIENTAS DE SALIDA ---
    st.subheader("🛠️ HERRAMIENTAS DE SALIDA")
    
    # BOTÓN PPTX
    if st.button("🗣️ Generar PPTX (Resumen)"):
        if len(st.session_state.messages) < 2: st.error("Necesito historial de chat para resumir.")
        else:
            with st.spinner("Diseñando diapositivas..."):
                # Prompt especial para forzar salida JSON
                historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                prompt_pptx = f"""
                Basado en este historial de chat:\n{historial}\n
                Crea un resumen para una presentación de PowerPoint de 4 a 6 diapositivas.
                TU SALIDA DEBE SER ÚNICAMENTE UN JSON VÁLIDO con este formato exacto, sin texto antes ni después:
                [
                    {{"title": "Título Principal de la Presentación", "content": []}},
                    {{"title": "Título Diapositiva 2", "content": ["Punto clave 1", "Punto clave 2"]}},
                    {{"title": "Título Diapositiva 3", "content": ["Punto clave 1", "Punto clave 2"]}}
                ]
                """
                try:
                    genai.configure(api_key=api_key)
                    model_tool = genai.GenerativeModel('gemini-2.0-flash-exp', generation_config={"temperature": 0.1})
                    response_pptx = model_tool.generate_content(prompt_pptx)
                    # Limpiar respuesta para obtener solo el JSON
                    cleaned_json = response_pptx.text.strip().removeprefix("```json").removesuffix("```")
                    slide_data = json.loads(cleaned_json)
                    st.session_state.generated_pptx = generate_pptx_from_data(slide_data)
                    st.success("✅ PPTX Generado")
                except Exception as e: st.error(f"Error generando PPTX: {e}")

    # DESCARGA PPTX
    if st.session_state.generated_pptx:
        st.download_button("📥 Descargar Presentación.pptx", st.session_state.generated_pptx, "resumen_ia.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")

    # BOTÓN GRÁFICO
    if st.button("📊 Generar Gráfico (Datos)"):
         if len(st.session_state.messages) < 2: st.error("Necesito historial con datos.")
         else:
            with st.spinner("Extrayendo datos y graficando..."):
                historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                prompt_chart = f"""
                Analiza el historial de chat e identifica datos numéricos comparables para un gráfico de barras.
                TU SALIDA DEBE SER ÚNICAMENTE UN JSON VÁLIDO con este formato exacto, sin texto antes ni después. 
                Si no hay datos, devuelve un JSON con listas vacías.
                {{
                    "title": "Título del Gráfico",
                    "labels": ["Categoría A", "Categoría B", "Categoría C"],
                    "values": [10, 25, 15]
                }}
                """
                try:
                    genai.configure(api_key=api_key)
                    model_tool = genai.GenerativeModel('gemini-2.0-flash-exp', generation_config={"temperature": 0.1})
                    response_chart = model_tool.generate_content(prompt_chart)
                    cleaned_json = response_chart.text.strip().removeprefix("```json").removesuffix("```")
                    chart_data = json.loads(cleaned_json)
                    if not chart_data["values"]: st.warning("No encontré datos numéricos claros para graficar.")
                    else:
                        st.session_state.generated_chart = generate_chart_from_data(chart_data)
                        st.success("✅ Gráfico Generado")
                except Exception as e: st.error(f"Error generando gráfico: {e}")

    st.divider()

    # --- GESTIÓN DE SESIÓN Y FUENTES (Lo mismo de V10) ---
    st.subheader("💾 GESTIÓN")
    if len(st.session_state.messages) > 0:
        col1, col2 = st.columns(2)
        docx_file = create_chat_docx(st.session_state.messages)
        col1.download_button("📄 Acta", docx_file, "acta.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        chat_json = json.dumps(st.session_state.messages)
        col2.download_button("🧠 Backup", chat_json, "memoria.json", "application/json")
    else: st.info("Escribe para habilitar guardado.")
    
    uploaded_memory = st.file_uploader("Restaurar (.json)", type=['json'])
    if uploaded_memory and st.button("🔄 Cargar Memoria"):
        st.session_state.messages = json.load(uploaded_memory)
        st.rerun()
    st.divider()
    st.subheader("📥 FUENTES")
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Lote Docs", "👁️ Media", "🔴 YT", "🌐 Web"])
    with tab1:
        uploaded_docs = st.file_uploader("PDF/Word Masivo", type=['pdf', 'docx'], accept_multiple_files=True)
        if uploaded_docs and st.button(f"🧠 Procesar {len(uploaded_docs)}"):
            texto_acumulado = ""
            barra = st.progress(0)
            with st.spinner("Leyendo..."):
                for i, doc in enumerate(uploaded_docs):
                    if doc.type == "application/pdf": c = get_pdf_text(doc)
                    else: c = get_docx_text(doc)
                    texto_acumulado += f"\n--- {doc.name} ---\n{c}\n------\n"
                    barra.progress((i + 1) / len(uploaded_docs))
            st.session_state.contexto_texto = texto_acumulado
            st.session_state.info_archivos = f"{len(uploaded_docs)} archivos."
            st.success("✅ Cargado")
        if st.session_state.info_archivos != "Ninguno": st.caption(f"Memoria: {st.session_state.info_archivos}")
    with tab2:
        uploaded_media = st.file_uploader("Media", type=['mp4', 'png', 'jpg', 'mp3', 'wav'])
        if uploaded_media and api_key and st.button("Subir Media"):
            genai.configure(api_key=api_key)
            with st.spinner("Procesando..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_media.name.split('.')[-1]) as tf:
                    tf.write(uploaded_media.read())
                    tp = tf.name
                mf = genai.upload_file(path=tp)
                while mf.state.name == "PROCESSING": time.sleep(1); mf = genai.get_file(mf.name)
                st.session_state.archivo_multimodal = mf
                st.success("✅ Listo"); os.remove(tp)
    with tab3:
        if st.button("Leer YT") and (u := st.text_input("Link YT")): st.session_state.contexto_texto = get_youtube_text(u); st.success("✅ YT")
    with tab4:
        if st.button("Leer Web") and (w := st.text_input("Link Web")): st.session_state.contexto_texto = get_web_text(w); st.success("✅ Web")
    if st.button("🗑️ Borrar Todo"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

# --- CHAT PRINCIPAL ---
st.title(f"🤖 Agente Constructor: {rol}")

if not api_key: st.warning("⚠️ Ingrese API Key."); st.stop()

# MOSTRAR GRÁFICO SI SE GENERÓ
if st.session_state.generated_chart:
    st.pyplot(st.session_state.generated_chart)
    if st.button("❌ Cerrar Gráfico"):
        st.session_state.generated_chart = None
        st.rerun()

genai.configure(api_key=api_key)
try: model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"temperature": temp_val})
except: st.error("Error Modelo"); st.stop()

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Instrucción..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            hc = st.session_state.contexto_texto != "" or st.session_state.archivo_multimodal is not None
            rf = "MODO ESTRICTO (Usar solo adjuntos)." if hc else "MODO CHAT GENERAL (Usar conocimiento libre)."
            ins = f"Actúa como {rol}.\nFECHA: {date.today()}\nCONTEXTO: {prompts_roles[rol]}\n{rf}\nESTILO: Natural, directo, sin clichés IA.\nAPA 7: Si hay DOI úsalo. Webs dinámicas usan 'Recuperado el {date.today()}'.\n"
            if st.session_state.contexto_texto: ins += f"\n--- DOCS ---\n{st.session_state.contexto_texto[:500000]}\n--- FIN ---\n"
            con = [ins]
            if st.session_state.archivo_multimodal: con.append(st.session_state.archivo_multimodal)
            hist = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
            con.append(f"\nHISTORIAL:\n{hist}\nSOLICITUD: {prompt}")
            res = model.generate_content(con)
            st.markdown(res.text)
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            st.rerun()
