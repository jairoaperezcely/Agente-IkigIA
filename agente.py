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
import matplotlib.pyplot as plt
import seaborn as sns # Para estética académica superior
import os
import re
import json
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
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
    /* 1. Fondo base y tipografía */
    .stApp { background-color: #000000 !important; }
    
    /* 2. FORZAR TEXTO BLANCO EN CONTENEDORES DE CHAT (VERSIÓN WEB) */
    .stChatMessage, .stChatMessage div, .stChatMessage p, .stMarkdown, .stMarkdown p {
        color: #FFFFFF !important;
    }

    /* 3. Ajuste específico para bloques de texto en escritorio */
    div[data-testid="stMarkdownContainer"] > p {
        color: #FFFFFF !important;
    }

    /* 4. Estilo de los globos de chat */
    [data-testid="stChatMessage"] {
        background-color: #0A0A0A !important;
        border: 1px solid #1A1A1A !important;
        border-radius: 10px;
        margin-bottom: 10px;
    }

    /* 5. Títulos y etiquetas */
    h1, h2, h3, .section-tag {
        color: #00E6FF !important;
    }

    /* 6. Sidebar y entradas de texto */
    [data-testid="stSidebar"] { background-color: #080808 !important; }
    .stTextInput input { color: #FFFFFF !important; background-color: #111 !important; }
    
    /* 7. Botones con identidad IkigAI */
    .stButton button {
        border: 1px solid #00E6FF !important;
        color: #00E6FF !important;
        background-color: transparent !important;
    }
    .stButton button:hover {
        background-color: #00E6FF !important;
        color: #000000 !important;
    }
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
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

DB_PATH = "vector_db"
DATA_FOLDER = "biblioteca_master"

def actualizar_memoria_persistente():
    if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
    
    docs_text = []
    # Escaneo de archivos en la carpeta física
    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".pdf"):
            with open(os.path.join(DATA_FOLDER, file), "rb") as f:
                docs_text.append(get_pdf_text(f))
    
    if not docs_text: return "Carpeta vacía."

    # Fragmentación para búsqueda quirúrgica
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.create_documents(docs_text)
    
    # Creación de la base de datos vectorial
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_db = FAISS.from_documents(chunks, embeddings)
    vector_db.save_local(DB_PATH)
    return "✅ Biblioteca Master sincronizada."

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

# --- 3. MOTOR DE EXPORTACIÓN TÉCNICO-CIENTÍFICO DINÁMICO (V1.93) ---
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re
from io import BytesIO
from datetime import date
from pptx import Presentation

def clean_markdown(text):
    """Limpia asteriscos y residuos de markdown para rigor profesional."""
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    return text.strip()

def extraer_titulo_dictado(messages, indices_seleccionados):
    """Detecta títulos dictados en mayúsculas o con encabezado #."""
    if not indices_seleccionados:
        return "MANUAL TÉCNICO DE TELESALUD"
    
    primer_contenido = messages[indices_seleccionados[0]]["content"]
    lineas = [l.strip() for l in primer_contenido.split('\n') if l.strip()]
    
    for linea in lineas:
        # Filtro de ruido conversacional: ignora saludos de la IA
        if any(x in linea.upper() for x in ["COMO IKIGAI", "PRESENTO", "DOCTOR", "HOLA", "ESTIMADO"]):
            continue
        
        # Captura la primera línea sustancial (limpiando formato de título markdown)
        titulo_limpio = re.sub(r'^#+\s*', '', linea)
        if len(titulo_limpio) > 5:
            # Si el usuario lo dictó, vendrá en la estructura inicial del bloque
            return titulo_limpio.upper()
            
    return "DOCUMENTO ESTRATÉGICO DE GESTIÓN"

def download_word_compilado(indices_seleccionados, messages, role):
    """Genera Word Técnico con Portada Académica y Estándares APA 7."""
    doc = docx.Document()
    
    # --- CONFIGURACIÓN DE EXCELENCIA (Arial 11 / Justificado) ---
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(12)
    style.paragraph_format.line_spacing = 1.15
    
    section = doc.sections[0]
    for m in ['left', 'right', 'top', 'bottom']:
        setattr(section, f'{m}_margin', Inches(1)) # Márgenes de 2.54cm
    
    # Detección del título dictado o inferido
    titulo_final = extraer_titulo_dictado(messages, indices_seleccionados)

    # PORTADA ACADÉMICA Y AUTORÍA FIJA
    t = doc.add_heading(titulo_final, 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in t.runs:
        run.font.name = 'Arial'
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0, 32, 96) # Azul Oxford Ejecutivo

    doc.add_paragraph("").add_run() # Espacio
    autor_p = doc.add_paragraph()
    run_a = autor_p.add_run("Jairo Antonio Pérez Cely")
    run_a.bold = True
    run_a.font.size = Pt(12)
    autor_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Identidad Profesional Polivalente
    doc.add_paragraph("Estratega en Salud Digital, Innovación y Alta Gerencia").alignment = 1
    doc.add_paragraph(f"Generado por IkigAI Executive Hub | {date.today()}").alignment = 1
    doc.add_paragraph("_" * 65).alignment = 1
    
    for idx in sorted(indices_seleccionados):
        content = messages[idx]["content"]
        lineas = content.split('\n')
        
        for line in lineas:
            # Limpieza de metadatos conversacionales de la IA
            if any(x in line.upper() for x in ["COMO IKIGAI", "PRESENTO", "DOCTOR"]): continue
            
            clean_line = re.sub(r'\*+', '', line).strip()
            if not clean_line: continue
            
            if line.startswith('#'):
                level = line.count('#')
                h = doc.add_heading(clean_line, level=min(level, 3))
                h.paragraph_format.keep_with_next = True # Control de viudas/huérfanas
                h.paragraph_format.space_before = Pt(18)
                for run in h.runs: run.font.name = 'Arial'
            
            elif line.strip().startswith(('*', '-', '•')) or re.match(r'^\d+\.', line.strip()):
                style_name = 'List Number' if re.match(r'^\d+\.', line.strip()) else 'List Bullet'
                p = doc.add_paragraph(re.sub(r'^[\*\-\•\d\.]+\s*', '', clean_line), style=style_name)
                p.paragraph_format.left_indent = Inches(0.25)
            
            else:
                p = doc.add_paragraph(clean_line)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        doc.add_page_break() # Salto de página entre secciones del manual
    
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

def download_pptx(content, role):
    """Genera Presentación Ejecutiva con ajuste automático de texto y segmentación."""
    prs = Presentation()
    clean_text = clean_markdown(content)
    
    # 1. SLIDE DE PORTADA
    lineas = [l for l in clean_text.split('\n') if l.strip() and not any(x in l.upper() for x in ["COMO IKIGAI", "DOCTOR"])]
    titulo_doc = extraer_titulo_dictado(st.session_state.messages, st.session_state.export_pool)
    
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = titulo_doc
    slide.placeholders[1].text = f"Autor: Jairo Antonio Pérez Cely\n{role} | {date.today()}"

    # 2. PROCESAMIENTO DE CONTENIDO TÉCNICO
    # Segmentamos el texto en bloques de máximo 600 caracteres para evitar desbordamiento
    bloques = [lineas[i:i + 4] for i in range(1, len(lineas), 4)] # Máximo 4 párrafos por slide
    
    for i, bloque in enumerate(bloques):
        slide = prs.slides.add_slide(prs.slide_layouts[1]) # Layout de Título y Cuerpo
        
        # Título de la diapositiva dinámico
        slide.shapes.title.text = f"{titulo_doc} (Parte {i+1})"
        
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.word_wrap = True # Forzamos el ajuste de línea
        
        for p_text in bloque:
            p = tf.add_paragraph()
            p.text = p_text.strip()
            p.font.size = Pt(18) # Tamaño ejecutivo legible
            p.space_after = Pt(10)
            
    bio = BytesIO()
    prs.save(bio)
    return bio.getvalue()

def download_excel(content):
    """Detecta tablas en el contenido y las exporta a un archivo Excel real."""
    try:
        lines = content.split('\n')
        table_data = []
        for line in lines:
            if '|' in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells:
                    table_data.append(cells)
        
        if len(table_data) > 1:
            table_data = [row for row in table_data if not all(set(c).issubset({'-', ':', ' '}) for c in row)]
            df = pd.DataFrame(table_data[1:], columns=table_data[0])
            
            bio = BytesIO()
            with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Datos_IkigAI')
            return bio.getvalue()
    except Exception as e:
        return None
    return None
    
def generar_grafico_estratégico(df, titulo="Análisis de Tendencias"):
    """Genera un gráfico profesional y lo devuelve como imagen para exportación."""
    plt.style.use('dark_background') # Estilo Zen acorde a su interfaz
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Tomamos las dos primeras columnas para un gráfico genérico de barras
    df.plot(kind='bar', x=df.columns[0], y=df.columns[1], ax=ax, color='#00E6FF')
    
    plt.title(titulo, fontsize=14, color='#00E6FF', pad=20)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    plt.close(fig)
    return buf.getvalue()
    
# --- 4. LÓGICA DE ESTADO ---
if "biblioteca" not in st.session_state: st.session_state.biblioteca = {rol: "" for rol in ROLES.keys()}
if "messages" not in st.session_state: st.session_state.messages = []
if "last_analysis" not in st.session_state: st.session_state.last_analysis = ""
if "export_pool" not in st.session_state: st.session_state.export_pool = []
if "editor_version" not in st.session_state: st.session_state.editor_version = 0

# --- 5. BARRA LATERAL: CONTROL ESTRATÉGICO Y ENTREGABLES (V2.0) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00E6FF; font-size: 40px;'>🧬</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; letter-spacing: 5px; font-size: 24px;'>IKIGAI</h2>", unsafe_allow_html=True)
    
    # 1. GESTIÓN DE SESIÓN
    st.divider()
    st.markdown("<div class='section-tag'>SESIÓN</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Reiniciar"):
            st.session_state.messages = []; st.session_state.export_pool = []; st.rerun()
    with c2:
        st.download_button("💾 Guardar", data=exportar_sesion(), file_name=f"Sesion_{date.today()}.json")

    # 2. PERFIL ESTRATÉGICO
    st.divider()
    st.markdown("<div class='section-tag'>PERFIL ESTRATÉGICO</div>", unsafe_allow_html=True)
    rol_activo = st.radio("Rol:", options=list(ROLES.keys()), label_visibility="collapsed")

     # 3. ENTREGABLES DINÁMICOS
    pool_actual = st.session_state.get("export_pool", [])
    if pool_actual:
        st.divider()
        st.markdown(f"<div class='section-tag'>REPORTES ({len(pool_actual)})</div>", unsafe_allow_html=True)
        # Word
        word_data = download_word_compilado(pool_actual, st.session_state.messages, rol_activo)
        st.download_button("📄 Generar Word", data=word_data, file_name=f"Reporte_{date.today()}.docx", use_container_width=True)
        # PPT
        ppt_cont = "\n\n".join([st.session_state.messages[idx]["content"] for idx in sorted(pool_actual)])
        st.download_button("📊 Generar PPT", data=download_pptx(ppt_cont, rol_activo), file_name=f"Presentacion_{date.today()}.pptx", use_container_width=True)
    else:
        st.divider()
        st.info("💡 Seleccione bloques con 📥 para exportar.")
        
    # 4. FUENTES DE CONTEXTO ---
    # --- 4. FUENTES DE CONTEXTO ---
    st.divider()
    st.markdown("<div class='section-tag'>FUENTES DE CONTEXTO</div>", unsafe_allow_html=True)
    tab_doc, tab_url, tab_img = st.tabs(["📄 DOC", "🔗 URL", "🖼️ IMG"])
    
    # --- PESTAÑA DOCUMENTOS ---
    with tab_doc:
        # Esta línea DEBE tener sangría (4 espacios)
        up = st.file_uploader("Subir PDF, Word o PPTX:", type=['pdf', 'docx', 'pptx'], accept_multiple_files=True, label_visibility="collapsed")
        
        if st.button("🧠 Procesar documentos", use_container_width=True):
            raw_text = ""
            for f in up:
                if f.type == "application/pdf":
                    raw_text += get_pdf_text(f)
                elif f.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    raw_text += get_docx_text(f)
                elif f.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                    # Lógica para extraer texto de PowerPoint
                    from pptx import Presentation
                    prs = Presentation(f)
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                raw_text += shape.text + " "
            
            with st.spinner("Refinando evidencia técnica..."):
                try:
                    # Usamos 1.5-flash para estabilidad total
                    refiner = genai.GenerativeModel('gemini-1.5-flash')
                    prompt_res = f"Extrae datos, normas y referencias clave: {raw_text[:45000]}"
                    resumen = refiner.generate_content(prompt_res)
                    st.session_state.biblioteca[rol_activo] = resumen.text
                    st.success("Biblioteca actualizada con PPTX/DOC/PDF.")
                except Exception as e:
                    st.session_state.biblioteca[rol_activo] = raw_text[:30000]
                    st.warning("Cargado sin refinamiento por límite de tokens.")
    # --- PESTAÑA URL (WEB SCRAPING) ---
    with tab_url:
        url_input = st.text_input("Pegar enlace web:", placeholder="https://ejemplo.com/protocolo")
        if st.button("🌐 Analizar Enlace", use_container_width=True) and url_input:
            with st.spinner("Navegando y sintetizando web..."):
                try:
                    # Usamos el modelo para que 'lea' la web (requiere que el modelo tenga acceso a internet o pasarle el html)
                    # Por simplicidad operativa, le pediremos al modelo que analice la URL directamente
                    refiner = genai.GenerativeModel('gemini-2.5-flash')
                    prompt_url = f"Accede o analiza la información clave de esta URL para mi contexto estratégico: {url_input}"
                    resumen_web = refiner.generate_content(prompt_url)
                    st.session_state.biblioteca[rol_activo] = resumen_web.text
                    st.success("Contexto web integrado.")
                except:
                    st.error("No se pudo extraer contenido de la URL.")

    # --- PESTAÑA IMG (VISIÓN) ---
    with tab_img:
        up_img = st.file_uploader("Subir imagen (Infografías, Tablas):", type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")
        if up_img and st.button("👁️ Analizar Imagen", use_container_width=True):
            with st.spinner("Interpretando evidencia visual..."):
                try:
                    import PIL.Image
                    img = PIL.Image.open(up_img)
                    refiner = genai.GenerativeModel('gemini-2.5-flash')
                    # Gemini analiza la imagen y la convierte en descripción técnica
                    resumen_img = refiner.generate_content(["Describe técnicamente esta imagen, extrae datos numéricos, tablas o flujogramas para mi contexto de toma de decisiones.", img])
                    st.session_state.biblioteca[rol_activo] = resumen_img.text
                    st.success("Análisis visual integrado.")
                except Exception as e:
                    st.error(f"Error en visión: {e}")
    # 5. BIBLIOTECA MASTER
    
        # --- NODO DE INTELIGENCIA RAG ---
    st.divider()
    st.markdown("<div class='section-tag'>CENTRO DE INTELIGENCIA RAG</div>", unsafe_allow_html=True)
    st.caption("Foco: Estrategia, UCI y Transformación Digital")

    if st.button("🧠 Sincronizar memoria máster", use_container_width=True):
        with st.spinner("Estudiando biblioteca y actualizando redes neuronales..."):
            try:
                # LLAMADA LIMPIA A LA FUNCIÓN DEL BLOQUE A
                resultado_sincro = actualizar_memoria_persistente()
                
                if "✅" in resultado_sincro:
                    st.success(resultado_sincro)
                    st.toast("Cerebro actualizado", icon="🧠")
                else:
                    st.warning(resultado_sincro)
                    
            except Exception as e:
                st.error(f"Error de ejecución en interfaz: {e}")
def actualizar_memoria_persistente():
    import os
    # 1. Auditoría de ubicación
    cwd = os.getcwd() # Directorio de trabajo actual
    all_folders = [d for d in os.listdir(cwd) if os.path.isdir(d)]
    
    # Intentar localizar la carpeta 'biblioteca_master'
    target_dir = os.path.join(cwd, "biblioteca_master")
    
    if "biblioteca_master" not in all_folders:
        return f"❌ ERROR DE LOCALIZACIÓN: El servidor está en '{cwd}'. Carpetas visibles: {all_folders}. No veo 'biblioteca_master'."

    docs_text = []
    archivos_encontrados = 0

    # 2. Escaneo con depuración
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                ruta_completa = os.path.join(root, file)
                try:
                    with open(ruta_completa, "rb") as f:
                        texto = get_pdf_text(f)
                        if texto and texto.strip():
                            docs_text.append(texto)
                            archivos_encontrados += 1
                except Exception as e:
                    print(f"Error en {file}: {e}")

    if archivos_encontrados == 0:
        contenido_interno = os.listdir(target_dir)
        return f"⚠️ CARPETA ENCONTRADA, PERO VACÍA: Visto en 'biblioteca_master': {contenido_interno}. ¿Subió los archivos a GitHub?"

    # 3. Procesamiento RAG (FAISS)
    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
        final_docs = splitter.create_documents(docs_text)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_db = FAISS.from_documents(final_docs, embeddings)
        vector_db.save_local(DB_PATH)
        return f"✅ ÉXITO: {archivos_encontrados} documentos integrados desde {target_dir}."
    except Exception as e:
        return f"❌ Error en motor RAG: {str(e)}"        
# --- 6. PANEL CENTRAL: WORKSTATION (V3.5 - INTEGRACIÓN RAG & EDICIÓN) ---

# 1. ESTILO Y ERGONOMÍA (Zen & Clean)
st.markdown("""
    <style>
    div[data-testid="stChatInput"] { border: none !important; background-color: transparent !important; }
    div[data-testid="stChatInput"] > div { border: none !important; background-color: transparent !important; }
    .stChatInput textarea {
        min-height: 100px !important;
        background-color: #262730 !important;
        border: 1px solid #00E6FF !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
        font-size: 17px !important;
        padding: 15px !important;
    }
    .stChatInput textarea:focus { border: 2px solid #00E6FF !important; box-shadow: 0 0 15px rgba(0, 230, 255, 0.3) !important; }
    </style>
""", unsafe_allow_html=True)

# Recuperamos versión para llaves dinámicas (Cierre automático de editores)
ver = st.session_state.get("editor_version", 0)

# --- 6. PANEL CENTRAL: WORKSTATION V3.5 (INTEGRACIÓN TOTAL) ---

# [Mantener el renderizado de historial y editores igual que su código...]

# --- CAPTURA DE NUEVO INPUT CON FUSIÓN DE FUENTES ---
if pr := st.chat_input("Nuestro reto para hoy..."):
    # 1. Registro del mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": pr})
    with st.chat_message("user"): 
        st.markdown(pr)
    
    with st.chat_message("assistant"):
        try:
            # --- CAPA 1: RECUPERACIÓN RAG (BIBLIOTECA GITHUB) ---
            contexto_rag = ""
            if os.path.exists(DB_PATH):
                with st.spinner("Consultando Biblioteca Master..."):
                    emb = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                    vdb = FAISS.load_local(DB_PATH, emb, allow_dangerous_deserialization=True)
                    docs = vdb.similarity_search(pr, k=3)
                    contexto_rag = "\n".join([f"- {d.page_content}" for d in docs])

            # --- CAPA 2: RECUPERACIÓN CONTEXTO SIDEBAR (DOC/URL/IMG) ---
            contexto_sidebar = st.session_state.biblioteca.get(rol_activo, "")

            # --- CAPA 3: ENSAMBLAJE DEL PROMPT MAESTRO DINÁMICO ---
            etiqueta_rol = rol_activo.upper()
            
            prompt_maestro = f"""
            ESTABLECER CONTEXTO PARA: {etiqueta_rol}
            
            FUENTES DISPONIBLES:
            1. CONTEXTO RECIENTE (SIDEBAR): 
            {contexto_sidebar if contexto_sidebar else "Sin archivos adicionales en esta sesión."}
            
            2. MEMORIA MÁSTER (PROTOCOLOS GITHUB): 
            {contexto_rag if contexto_rag else "Sin evidencia específica en biblioteca persistente."}
            
            INSTRUCCIÓN EJECUTIVA:
            Como {rol_activo}, analiza la consulta del usuario. 
            Prioriza la información del Contexto Reciente si existe, pero valídala 
            contra la Memoria Máster. Mantén rigor técnico, citas APA 7 y tono ejecutivo.
            
            CONSULTA DEL {etiqueta_rol}: {pr}
            """

            # --- CAPA 4: INFERENCIA CON MODELO CORRECTO ---
            # Nota: Cambiado a gemini-1.5-flash para estabilidad
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Generación con indicador de pensamiento
            with st.spinner(f"IkigAI pensando como {rol_activo}..."):
                resp = model.generate_content(prompt_maestro)
                
                # Respuesta humana y cierre operativo
                respuesta_final = resp.text
                if "Punto Ciego" not in respuesta_final:
                    respuesta_final += f"\n\n---\n**Pregunta de Punto Ciego:** ¿Hemos evaluado cómo este análisis impacta el ROI cognitivo del rol {rol_activo} a largo plazo?"

            st.markdown(respuesta_final)
            st.session_state.messages.append({"role": "assistant", "content": respuesta_final})
            st.rerun()

        except Exception as e:
            st.error(f"Error en el motor de inteligencia: {e}")
            st.info("Sugerencia: Verifique que la API Key y la conexión a la base de datos vectorial sean correctas.")







