import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
from datetime import date
from pptx import Presentation
from pptx.util import Inches, Pt
import os
import re
import json

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(
    page_title="IkigAI V1.86 - Executive Workstation", 
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
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, h2, h3 { color: #FFFFFF !important; }
    [data-testid="stChatMessage"] { background-color: #050505 !important; border: 1px solid #1A1A1A !important; }
    .stMarkdown p, .stMarkdown li { color: #FFFFFF !important; font-size: 16px !important; line-height: 1.7 !important; }
    .stDownloadButton button, .stButton button { width: 100%; border-radius: 4px; background-color: transparent !important; color: #00E6FF !important; border: 1px solid #00E6FF !important; font-weight: 600; }
    .stDownloadButton button:hover, .stButton button:hover { background-color: #00E6FF !important; color: #000000 !important; }
    .section-tag { font-size: 11px; color: #666; letter-spacing: 1.5px; margin: 15px 0 5px 0; font-weight: 600; }
    .stExpander { border: 1px solid #1A1A1A !important; background-color: #050505 !important; border-radius: 8px !important; }
    textarea { background-color: #0D1117 !important; color: #FFFFFF !important; border: 1px solid #00E6FF !important; font-family: 'Courier New', monospace !important; font-size: 14px !important; }
    /* Estilo Checkbox de Selección */
    .stCheckbox { background-color: #111; padding: 5px; border-radius: 5px; border: 1px solid #333; margin-top: 10px; }
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

# --- 2. FUNCIONES DE LECTURA Y PERSISTENCIA ---
def get_pdf_text(f): return "".join([p.extract_text() for p in PdfReader(f).pages])
def get_docx_text(f): return "\n".join([p.text for p in docx.Document(f).paragraphs])
def get_excel_text(f): return pd.read_excel(f).to_string()

def exportar_sesion():
    mensajes_finales = []
    for i, msg in enumerate(st.session_state.messages):
        nuevo_msg = msg.copy()
        if msg["role"] == "assistant" and f"edit_{i}" in st.session_state:
            nuevo_msg["content"] = st.session_state[f"edit_{i}"]
        mensajes_finales.append(nuevo_msg)
    data = {"biblioteca": st.session_state.biblioteca, "messages": mensajes_finales, "last_analysis": st.session_state.last_analysis}
    return json.dumps(data, indent=4)

def cargar_sesion(json_data):
    data = json.loads(json_data)
    st.session_state.biblioteca = data["biblioteca"]
    st.session_state.messages = data["messages"]
    st.session_state.last_analysis = data["last_analysis"]

# --- 3. MOTOR DE EXPORTACIÓN COMPILADA (V1.87) ---
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def download_word_compilado(indices_seleccionados, messages, role):
    doc = docx.Document()
    
    # Configuración de Estilo Base (Arial 11)
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # Configuración de márgenes técnicos (2.54 cm)
    section = doc.sections[0]
    for margin in ['left', 'right', 'top', 'bottom']:
        setattr(section, f'{margin}_margin', Inches(1))
    
    # LÓGICA DE TÍTULO DINÁMICO SEGÚN CONTENIDO
    # Extraemos el contenido del primer bloque seleccionado para el título
    primer_bloque = messages[indices_seleccionados[0]]["content"] if indices_seleccionados else ""
    lineas = [l.strip() for l in primer_bloque.split('\n') if l.strip()]
    # Si la primera línea empieza con # (Markdown), la limpiamos
    titulo_texto = re.sub(r'^#+\s*', '', lineas[0]) if lineas else "MANUAL TÉCNICO DE TELESALUD"

    # PORTADA TÉCNICA
    header = doc.add_heading(titulo_texto.upper(), 0)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in header.runs:
        run.font.name = 'Arial'
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0, 32, 96) # Azul Ejecutivo
    
    doc.add_paragraph(f"Perfil Emisor: {role.upper()}").alignment = 1
    doc.add_paragraph(f"Fecha de Generación: {date.today()}").alignment = 1
    doc.add_paragraph("_" * 75).alignment = 1
    
    for idx in sorted(indices_seleccionados):
        content = messages[idx]["content"]
        # Evitamos repetir el título que ya pusimos en la portada si es la primera línea
        lineas_bloque = content.split('\n')
        
        for i, line in enumerate(lineas_bloque):
            clean_line = re.sub(r'\*+', '', line).strip()
            if not clean_line: continue
            
            # Gestión de Títulos Internos
            if line.startswith('#'):
                level = line.count('#')
                h = doc.add_heading(clean_line, level=min(level, 3))
                h.paragraph_format.space_before = Pt(18)
                for run in h.runs: run.font.name = 'Arial'
            
            # Listas con Sangría Técnica (0.63 cm)
            elif line.strip().startswith(('*', '-', '•')) or re.match(r'^\d+\.', line.strip()):
                style_name = 'List Number' if re.match(r'^\d+\.', line.strip()) else 'List Bullet'
                text_only = re.sub(r'^[\*\-\•\d\.]+\s*', '', clean_line)
                p = doc.add_paragraph(text_only, style=style_name)
                p.paragraph_format.left_indent = Inches(0.25)
            
            # Cuerpo de Texto Justificado
            else:
                p = doc.add_paragraph(clean_line)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(12)
        
        doc.add_page_break()
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()
    
def download_pptx(content, role):
    """Genera una presentación con título dinámico basado en la primera línea."""
    prs = Presentation()
    clean_content = clean_markdown(content)
    
    # Segmentación para slides (basado en párrafos o puntos)
    segments = [s.strip() for s in re.split(r'\n|\. ', clean_content) if len(s.strip()) > 25]
    
    # EXTRACCIÓN DINÁMICA DEL TÍTULO
    lineas = [l.strip() for l in clean_content.split('\n') if l.strip()]
    titulo_dinamico = lineas[0] if lineas else f"REPORTE: {role.upper()}"
    titulo_slide = (titulo_dinamico[:70] + '...') if len(titulo_dinamico) > 73 else titulo_dinamico

    # Slide de Título
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = titulo_slide.upper()
    slide.placeholders[1].text = f"Perfil de Gestión: {role}\nIkigAI Executive Hub | {date.today()}"
    
    # Slides de Contenido (Máximo 15)
    for i, segment in enumerate(segments[1:16]):
        bullet_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(bullet_layout)
        slide.shapes.title.text = f"Análisis Estratégico {i+1}"
        
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.text = (segment[:447] + '...') if len(segment) > 450 else segment
        
    bio = BytesIO()
    prs.save(bio)
    return bio.getvalue()
    
# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "export_pool" not in st.session_state: st.session_state.export_pool = []

# --- 5. BARRA LATERAL: CONTROL TOTAL Y FUENTES DE CONTEXTO ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    st.divider()
    st.markdown("<div class='section-tag'>SESIÓN</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reiniciar"):
            st.session_state.messages = []
            st.session_state.export_pool = []
            st.rerun()
    with col2:
        st.download_button(
            label="💾 Guardar",
            data=exportar_sesion(),
            file_name=f"IkigAI_Turno_{date.today()}.json",
            mime="application/json"
        )
    
    st.divider()
    st.markdown("<div class='section-tag'>PERFIL ESTRATÉGICO</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol activo:", options=list(ROLES.keys()), label_visibility="collapsed")
    
    # --- BLOQUE DINÁMICO DE EXPORTACIÓN (Solo Selección) ---
    if st.session_state.export_pool:
        st.divider()
        st.markdown(f"<div class='section-tag'>ENTREGABLES ({len(st.session_state.export_pool)} BLOQUES)</div>", unsafe_allow_html=True)
        
        # Word Compilado
        word_data = download_word_compilado(st.session_state.export_pool, st.session_state.messages, rol_activo)
        st.download_button(
            "📄 Generar Word", 
            data=word_data, 
            file_name=f"Manual_{rol_activo}.docx", 
            use_container_width=True
        )
        
        # PPT Compilado
        contenido_para_ppt = "\n\n".join([st.session_state.messages[idx]["content"] for idx in sorted(st.session_state.export_pool)])
        ppt_data = download_pptx(contenido_para_ppt, rol_activo)
        st.download_button(
            "📊 Generar PPT", 
            data=ppt_data, 
            file_name=f"Presentacion_{rol_activo}.pptx", 
            use_container_width=True
        )
    else:
        st.info("Seleccione bloques con 📥 para exportar.")

    # --- RESTAURACIÓN DE FUENTES DE CONTEXTO ---
    st.divider()
    st.markdown("<div class='section-tag'>FUENTES DE CONTEXTO</div>", unsafe_allow_html=True)
    
    tab_doc, tab_url, tab_img = st.tabs(["DOC", "URL", "IMG"])
    
    with tab_doc:
        up = st.file_uploader("Subir PDF o Word:", type=['pdf', 'docx'], accept_multiple_files=True, label_visibility="collapsed")
        if st.button("🧠 PROCESAR ARCHIVOS", use_container_width=True):
            raw_text = ""
            for f in up:
                if f.type == "application/pdf":
                    raw_text += get_pdf_text(f)
                else:
                    raw_text += get_docx_text(f)
            
            with st.spinner("Refinando contexto para el manual..."):
                try:
                    # MOTOR: Gemini 2.5 Flash
                    refiner = genai.GenerativeModel('gemini-2.5-flash')
                    prompt_resumen = f"Actúa como Secretario Técnico Académico. Extrae datos, normas y referencias clave de este texto para un manual de telesalud: {raw_text[:45000]}"
                    resumen = refiner.generate_content(prompt_resumen)
                    st.session_state.biblioteca[rol_activo] = resumen.text
                    st.success("Biblioteca actualizada.")
                except Exception as e:
                    st.warning("Fallo en IA. Cargando texto crudo.")
                    st.session_state.biblioteca[rol_activo] = raw_text[:30000]

    with tab_url:
        uw = st.text_input("URL de referencia:", placeholder="https://", label_visibility="collapsed")
        if st.button("🔗 CONECTAR WEB", use_container_width=True):
            try:
                r = requests.get(uw, timeout=10)
                sopa = BeautifulSoup(r.text, 'html.parser')
                st.session_state.biblioteca[rol_activo] += "\n" + sopa.get_text()
                st.success("Web integrada al contexto.")
            except:
                st.error("No se pudo conectar con la URL.")

    with tab_img:
        img_f = st.file_uploader("Subir imagen (Evidencia/Gráfica):", type=['jpg', 'png'], label_visibility="collapsed")
        if img_f:
            st.session_state.temp_image = Image.open(img_f)
            st.image(img_f, caption="Imagen cargada para análisis")

    st.divider()
    st.caption(f"IkigAI V1.87 | {date.today()}")
    
# --- 6. PANEL CENTRAL: WORKSTATION MÓVIL Y COMPILADOR ---
st.markdown(f"<h3 style='color: #00A3FF;'>{rol_activo.upper()}</h3>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(msg["role"]):
        # 1. LECTURA SIEMPRE DISPONIBLE (Markdown Limpio)
        st.markdown(msg["content"])
        
        if msg["role"] == "assistant":
            # 2. SELECCIÓN PARA EL MANUAL (Checkbox)
            # Verificamos si el índice está en el pool para mantener el estado visual
            is_selected = i in st.session_state.export_pool
            if st.checkbox(f"📥 Incluir en Manual (Word)", key=f"sel_{i}", value=is_selected):
                if i not in st.session_state.export_pool:
                    st.session_state.export_pool.append(i)
            else:
                if i in st.session_state.export_pool:
                    st.session_state.export_pool.remove(i)

            # 3. GESTIÓN INDIVIDUAL (Copiar/Editar)
            with st.expander("🛠️ GESTIONAR ESTE BLOQUE", expanded=False):
                t_copy, t_edit = st.tabs(["📋 COPIAR", "📝 EDITAR"])
                
                with t_copy:
                    st.code(msg["content"], language=None)
                    st.caption("Toque el icono superior derecho para copiar.")
                
                with t_edit:
                    # Editor con altura optimizada
                    texto_editado = st.text_area(
                        "Modifique el borrador aquí:", 
                        value=msg["content"], 
                        height=400, 
                        key=f"edit_{i}",
                        label_visibility="collapsed"
                    )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Botón de fijado visual y ancho (Mobile Ready)
                    if st.button("✅ FIJAR CAMBIOS EN ESTE BLOQUE", key=f"save_{i}", use_container_width=True):
                        # Actualizamos el mensaje en el historial para que la exportación use la versión editada
                        st.session_state.messages[i]["content"] = texto_editado
                        st.session_state.last_analysis = texto_editado
                        st.toast("✅ Cambios guardados y sincronizados.")
        
        st.markdown("---")

# Captura de nuevo input
if pr := st.chat_input("¿Qué sección del manual diseñamos ahora, Doctor?"):
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"):
        st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            sys_context = f"Rol: {rol_activo}. {ROLES[rol_activo]}. Rigor académico APA 7."
            lib_context = st.session_state.biblioteca.get(rol_activo, '')[:500000]
            
            response = model.generate_content([sys_context, f"Contexto: {lib_context}", pr])
            
            # Guardamos en historial pero NO marcamos para exportar automáticamente
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")






