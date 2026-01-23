import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Pt as PtxPt
from pptx.dml.color import RGBColor as PtxRGB
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os
from io import BytesIO
import json
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder
from datetime import datetime, date

# ==========================================
# 🏛️ CONFIGURACIÓN DE IDENTIDAD UNAL
# ==========================================
st.set_page_config(page_title="IkigAI: Ecosistema Directivo", page_icon="🏛️", layout="wide")

# Colores Institucionales UNAL
UNAL_AZUL = "#003366"
UNAL_GRIS = "#f0f2f6"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: {UNAL_GRIS} !important; border-right: 3px solid {UNAL_AZUL}; }}
    .reportview-container .main .block-container {{ padding-top: 2rem; }}
    h1 {{ color: {UNAL_AZUL}; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🧠 MEMORIA MAESTRA Y LÓGICA DE NEGOCIO
# ==========================================
MEMORIA_MAESTRA = """
PERFIL: Eres el Asesor Principal del Vicedecano de Medicina UNAL, del Director de UCI, del Constultor en salud digital, el profesor universitario y asistente personal ejecutivo
COMPETENCIAS: Epidemiología, Bioética, Telemedicina y Gestión de Proyectos bajo Ley 1419.
ESTILO: Académico de alto nivel, ejecutivo, preciso y basado en evidencia.
PROTOCOLO: 
1. Si los datos son numéricos, genera una tabla Y un breve análisis de tendencias.
2. Si la consulta es médica, incluye una sección de 'Consideraciones Bioéticas'.
3. Formato: Usa Markdown con encabezados claros.
"""

# ==========================================
# 📊 MÓDULO DE INTELIGENCIA DE DATOS
# ==========================================
def analizar_excel_avanzado(file):
    df = pd.read_excel(file)
    st.write("### 📈 Previsualización de Datos Institucionales")
    st.dataframe(df.head(5), use_container_width=True)

    num_cols = df.select_dtypes(include=['number']).columns
    if not num_cols.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        df[num_cols[0]].plot(kind='line' if len(df)>10 else 'bar', ax=ax, color=UNAL_AZUL)
        plt.title(f"Tendencia de {num_cols[0]}")
        st.pyplot(fig)
    return df.to_string()

# ==========================================
# 📄 GENERADOR DE DOCUMENTOS NORMATIVOS (WORD)
# ==========================================
def create_executive_docx(content):
    doc = docx.Document()
    section = doc.sections[0]
    header = section.header
    header.paragraphs[0].text = "UNIVERSIDAD NACIONAL DE COLOMBIA - FACULTAD DE MEDICINA"

    p = doc.add_paragraph("INFORME TÉCNICO DE DIRECCIÓN")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.runs[0]
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0, 51, 102)

    for line in content.split('\n'):
        if line.startswith('#'):
            doc.add_heading(line.replace('#', '').strip(), level=1)
        else:
            doc.add_paragraph(line)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# 🧭 AGENTE PERSONAL MULTIPERFIL
# ==========================================
def analizar_prioridades(contexto):
    prioridades = {
        "urgente_importante": [],
        "alto_impacto": [],
        "posible_procrastinacion": []
    }
    for tarea in contexto["tareas"]:
        if "urgente" in tarea or "crítico" in tarea:
            prioridades["urgente_importante"].append(tarea)
        elif "estrategia" in tarea or "innovación" in tarea:
            prioridades["alto_impacto"].append(tarea)
        else:
            prioridades["posible_procrastinacion"].append(tarea)
    return prioridades

def ejercicio_pensamiento_critico():
    return "¿Qué creencia no cuestionada podría estar limitando mi efectividad hoy en alguno de mis tres roles?"

def dinamica_creativa():
    return "Rediseña uno de tus procesos actuales (clínico, académico o consultivo) eliminando pasos redundantes e introduciendo una solución digital disruptiva."

def generar_retroalimentacion(contexto, prioridades):
    resumen = f"### 🗓️ Fecha: {contexto['fecha']}\n\n#### 🔍 Prioridades:\n"
    for categoria, tareas in prioridades.items():
        resumen += f"- **{categoria.replace('_', ' ').title()}**: {len(tareas)} tareas\n"
    resumen += "\n---\n#### 🧠 Pensamiento Crítico:\n> " + ejercicio_pensamiento_critico()
    resumen += "\n\n#### 💡 Dinámica Creativa:\n> " + dinamica_creativa()
    return resumen

def ejecutar_agente_personal():
    tareas = ["Revisión de indicadores clínicos", "Preparar consejo de facultad", "Experto en salud digital y telesalud"]
    contexto = {
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "tareas": tareas,
        "objetivos": ["Optimizar flujo UCI", "Avance plan académico", "Escalar proyecto telesalud"],
        "estado_emocional": "Concentrado",
        "eventos": ["Reunión decanos", "Ronda clínica UCI"]
    }
    prioridades = analizar_prioridades(contexto)
    resumen = generar_retroalimentacion(contexto, prioridades)
    return resumen

# ==========================================
# 🚀 INTERFAZ Y FLUJO DE TRABAJO
# ==========================================
with st.sidebar:
    st.image("https://unal.edu.co/typo3conf/ext/unaltemplate/Resources/Public/images/escudo_unal.png", width=180)
    st.title("Panel de Control")

    api_key = st.secrets.get("GOOGLE_API_KEY") or st.text_input("Gemini API Key", type="password")

    if api_key:
        genai.configure(api_key=api_key)

    st.subheader("📁 Gestión de Insumos")
    uploaded_files = st.file_uploader("Cargar Actas, Resoluciones o Bases de Datos", accept_multiple_files=True)

    if st.button("🔄 Sincronizar Cerebro"):
        with st.spinner("Procesando documentos..."):
            full_context = ""
            for f in uploaded_files:
                if f.name.endswith('.pdf'): full_context += get_pdf_text(f)
                elif f.name.endswith('.docx'): full_context += get_docx_text(f)
                elif f.name.endswith(('.xlsx', '.xls')): full_context += analizar_excel_avanzado(f)
            st.session_state.contexto_texto = full_context
            st.success("Contexto actualizado.")

if st.button("🧭 Activar Agente Diario"):
    resumen = ejecutar_agente_personal()
    st.markdown(resumen)

st.info(f"📍 **Modo:** {rol if 'rol' in locals() else 'Socio Estratégico'} | **Contexto:** {len(st.session_state.get('contexto_texto', ''))} caracteres cargados.")

if prompt := st.chat_input("¿Qué reporte o análisis necesita hoy, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=MEMORIA_MAESTRA
        )

        contexto_limitado = st.session_state.get("contexto_texto", "")[:30000]
        full_prompt = f"CONTEXTO PREVIO: {contexto_limitado}\n\nINSTRUCCIÓN: {prompt}"

        response = model.generate_content(full_prompt)
        st.markdown(response.text)

        st.session_state.messages.append({"role": "assistant", "content": response.text})

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            doc_file = create_executive_docx(response.text)
            st.download_button("📩 Descargar como Word (Oficial)", doc_file, file_name=f"Informe_{date.today()}.docx")
