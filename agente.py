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
# LIBRERÍAS GRÁFICAS Y PPTX
from pptx import Presentation
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente V11.5 (Analista Gráfico Pro)", page_icon="📈", layout="wide")

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

# --- FUNCIÓN GENERAR POWERPOINT (PPTX) ---
def generate_pptx_from_data(slide_data):
    prs = Presentation()
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = slide_data[0].get("title", "Presentación IA")
    slide.placeholders[1].text = f"Fecha: {date.today().strftime('%d/%m/%Y')}"

    bullet_slide_layout = prs.slide_layouts[1]
    for slide_info in slide_data[1:]:
        slide = prs.slides.add_slide(bullet_slide_layout)
        slide.shapes.title.text = slide_info.get("title", "Título")
        tf = slide.placeholders[1].text_frame
        content_list = slide_info.get("content", [])
        if content_list:
            tf.text = content_list[0]
            for point in content_list[1:]:
                p = tf.add_paragraph()
                p.text = point
                p.level = 0
    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer

# --- NUEVA FUNCIÓN: MOTOR GRÁFICO AVANZADO (V11.5) ---
def generate_advanced_chart(chart_data):
    """Genera gráficos complejos (líneas, barras mixtas) desde JSON."""
    title = chart_data.get("title", "Análisis Gráfico")
    labels = chart_data.get("labels", [])
    datasets = chart_data.get("datasets", []) # Lista de series de datos

    # Configuración profesional del lienzo
    fig, ax = plt.subplots(figsize=(10, 5))
    plt.style.use('seaborn-v0_8-darkgrid') # Estilo más financiero/profesional

    # Iterar sobre cada serie de datos (ej: Línea MACD, Línea Señal, Barras Histograma)
    for ds in datasets:
        label_name = ds.get("label", "Serie")
        values = ds.get("values", [])
        chart_type = ds.get("type", "line").lower() # 'line' o 'bar'
        color = ds.get("color", None)

        # Validar que la longitud de los datos coincida con las etiquetas
        if len(values) != len(labels):
            st.warning(f"⚠️ Desajuste de datos en serie '{label_name}'. Se omitirá.")
            continue

        if chart_type == "line":
            # Dibujar Línea (Trading/Tendencias)
            ax.plot(labels, values, label=label_name, marker='o', markersize=4, linewidth=2, color=color)
        else:
            # Dibujar Barra (Volumen/Histograma) - con transparencia
            ax.bar(labels, values, label=label_name, alpha=0.5, color=color)

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylabel("Valor / Nivel")
    ax.legend(frameon=True) # Mostrar leyenda
    ax.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45, ha='right')
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
    temp_val = st.slider("Creatividad:", 0.0, 1.0, 0.2, 0.1)
    st.divider()
    rol = st.radio("Perfil Activo:", ["Vicedecano Académico", "Director de UCI", "Mentor de Trading", "Experto en Telesalud", "Investigador Científico", "Profesor universitario", "Asistente Personal"])
    prompts_roles = {
        "Vicedecano Académico": "Eres Vicedecano riguroso. Cita normativas.",
        "Director de UCI": "Eres Director de UCI. Prioriza seguridad y datos clínicos.",
        "Mentor de Trading": "Eres Trader Institucional (Smart Money). Analiza estructura, liquidez y riesgo con precisión.",
        "Experto en Telesalud": "Eres experto en Salud Digital y normativa.",
        "Investigador Científico": "Eres metodólogo. Prioriza validez estadística.",
        "Profesor universitario": "Eres docente socrático. Explica con claridad.",
        "Asistente Personal": "Eres asistente ejecutivo eficiente."
    }
    st.divider()
    
    # --- HERRAMIENTAS DE SALIDA (ACTUALIZADO V11.5) ---
    st.subheader("🛠️ HERRAMIENTAS DE SALIDA")
    
    # BOTÓN PPTX
    if st.button("🗣️ Generar PPTX (Resumen)"):
        if len(st.session_state.messages) < 2: st.error("Necesito historial.")
        else:
            with st.spinner("Diseñando diapositivas..."):
                historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                prompt_pptx = f"""Basado en:\n{historial}\nCrea resumen para PPTX de 4-6 slides. SALIDA JSON ÚNICAMENTE: [{{{"title": "T1", "content": []}}}, {{{"title": "T2", "content": ["P1", "P2"]}}}]"""
                try:
                    genai.configure(api_key=api_key)
                    model_tool = genai.GenerativeModel('gemini-2.0-flash-exp', generation_config={"temperature": 0.1})
                    response = model_tool.generate_content(prompt_pptx)
                    cleaned_json = response.text.strip().removeprefix("```json").removesuffix("```")
                    st.session_state.generated_pptx = generate_pptx_from_data(json.loads(cleaned_json))
                    st.success("✅ PPTX Listo")
                except Exception as e: st.error(f"Error PPTX: {e}")
    if st.session_state.generated_pptx:
        st.download_button("📥 Descargar Presentación.pptx", st.session_state.generated_pptx, "resumen_ia.pptx")

    # BOTÓN GRÁFICO AVANZADO (NUEVO PROMPT)
    if st.button("📈 Generar Gráfico Pro (Datos)"):
         if len(st.session_state.messages) < 2: st.error("Necesito historial con datos numéricos.")
         else:
            with st.spinner("Analizando datos complejos..."):
                historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                # PROMPT MUCHO MÁS SOFISTICADO PARA ESTRUCTURAR DATOS COMPLEJOS
                prompt_chart = f"""
                Actúa como Analista de Datos Financieros/Científicos. Analiza el historial reciente.
                Extrae datos numéricos y decide la mejor forma de graficarlos (Líneas para tendencias/tiempo, Barras para histogramas/categorías).
                TU SALIDA DEBE SER ÚNICAMENTE UN JSON VÁLIDO con este formato complejo exacto. Si no hay datos, "datasets": [].
                {{
                    "title": "Título del Análisis (ej: MACD vs Señal)",
                    "labels": ["T1", "T2", "T3", "T4"],  <-- Eje X (Tiempo/Categorías)
                    "datasets": [   <-- Lista de series
                        {{"label": "Línea Rápida (MACD)", "type": "line", "values": [1.2, 1.5, 1.3, 1.8], "color": "blue"}},
                        {{"label": "Línea Lenta (Señal)", "type": "line", "values": [1.3, 1.4, 1.4, 1.6], "color": "red"}},
                        {{"label": "Histograma", "type": "bar", "values": [-0.1, 0.1, -0.1, 0.2], "color": "grey"}}
                    ]
                }}
                HISTORIAL: {historial}
                """
                try:
                    genai.configure(api_key=api_key)
                    model_tool = genai.GenerativeModel('gemini-2.0-flash-exp', generation_config={"temperature": 0.1})
                    response = model_tool.generate_content(prompt_chart)
                    cleaned_json = response.text.strip().removeprefix("```json").removesuffix("```")
                    chart_data = json.loads(cleaned_json)
                    if not chart_data["datasets"]: st.warning("No encontré estructura de datos clara.")
                    else:
                        st.session_state.generated_chart = generate_advanced_chart(chart_data)
                        st.success("✅ Gráfico Pro Generado (Ver arriba)")
                except Exception as e: st.error(f"Error generando gráfico: {e}. Intenta pedir los datos más claros.")

    st.divider()
    st.subheader("💾 GESTIÓN"); 
    if len(st.session_state.messages)>0: c1,c2=st.columns(2);c1.download_button("📄Acta",create_chat_docx(st.session_state.messages),"acta.docx");c2.download_button("🧠JSON",json.dumps(st.session_state.messages),"memoria.json")
    if st.file_uploader("Restaurar",type=['json'])and st.button("Cargar"):st.session_state.messages=json.load(uploaded_memory);st.rerun()
    st.divider()
    if st.button("🗑️ Borrar Todo"): st.session_state.clear(); st.rerun()

# --- CHAT PRINCIPAL ---
st.title(f"🤖 Agente Analista: {rol}")
if not api_key: st.warning("⚠️ Ingrese API Key."); st.stop()

# MOSTRAR GRÁFICO PRO EN LA PARTE SUPERIOR
if st.session_state.generated_chart:
    st.pyplot(st.session_state.generated_chart)
    if st.button("❌ Cerrar Gráfico Visual"): st.session_state.generated_chart = None; st.rerun()

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
