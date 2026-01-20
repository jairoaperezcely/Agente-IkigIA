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
st.set_page_config(page_title="Agente IkigAI V13", page_icon="🧬", layout="wide")

# DEFINA AQUÍ SU MODELO PREFERIDO (Para cambiarlo fácil si sale uno nuevo)
MODELO_USADO = 'gemini-2.5-flash' 
# Si el 2.5 falla, cambie esta línea por: 'gemini-2.0-flash-exp' o 'gemini-1.5-flash'

# ==========================================
# FUNCIONES UTILITARIAS (LECTURA & GENERACIÓN)
# ==========================================

def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# 1. GENERAR WORD (ACTA - TODO EL HISTORIAL)
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading(f'Acta de Sesión: {date.today().strftime("%d/%m/%Y")}', 0)
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "ASISTENTE IA"
        doc.add_heading(role, level=2)
        doc.add_paragraph(msg["content"])
        doc.add_paragraph("---")
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 2. GENERAR WORD (LIMPIO - SOLO ÚLTIMO TEXTO)
def create_clean_docx(text_content):
    doc = docx.Document()
    # Limpieza básica de etiquetas markdown si las trae
    clean_text = text_content.replace("```markdown", "").replace("```", "")
    for paragraph in clean_text.split('\n'):
        if paragraph.strip(): 
            doc.add_paragraph(paragraph)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 3. GENERAR PPTX
def generate_pptx_from_data(slide_data):
    prs = Presentation()
    # Diapositiva Título
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = slide_data[0].get("title", "Presentación Generada")
    slide.placeholders[1].text = f"Generado el: {date.today()}"
    
    # Diapositivas de Contenido
    for info in slide_data[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = info.get("title", "Título")
        tf = slide.placeholders[1].text_frame
        content_list = info.get("content", [])
        if content_list:
            tf.text = content_list[0]
            for point in content_list[1:]:
                p = tf.add_paragraph()
                p.text = point
                p.level = 0
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

# 4. GENERAR EXCEL
def generate_excel_from_data(excel_data):
    output = BytesIO()
    # Usamos pandas con el motor openpyxl
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            # Limitar nombre de hoja a 30 chars (regla de Excel)
            safe_name = sheet_name[:30]
            df.to_excel(writer, index=False, sheet_name=safe_name)
    output.seek(0)
    return output

# 5. GENERAR GRÁFICO (MATPLOTLIB)
def generate_advanced_chart(chart_data):
    fig, ax = plt.subplots(figsize=(10, 5))
    plt.style.use('seaborn-v0_8-darkgrid')
    
    title = chart_data.get("title", "Gráfico")
    labels = chart_data.get("labels", [])
    datasets = chart_data.get("datasets", [])

    for ds in datasets:
        # Validar que coincidan los datos
        if len(ds["values"]) == len(labels):
            if ds.get("type") == "line":
                ax.plot(labels, ds["values"], label=ds["label"], marker='o', linewidth=2)
            else:
                ax.bar(labels, ds["values"], label=ds["label"], alpha=0.6)
        else:
            st.warning(f"⚠️ Datos incompletos en serie: {ds.get('label')}")

    ax.legend()
    ax.set_title(title, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig

# FUNCIONES WEB/YOUTUBE
def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "TRANSCRIPCIÓN YT:\n" + " ".join([i['text'] for i in t])
    except: return "No se pudo obtener transcripción de YT."

def get_web_text(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.content, 'html.parser')
        return "CONTENIDO WEB:\n" + "\n".join([p.get_text() for p in soup.find_all('p')])
    except Exception as e: return f"Error leyendo web: {str(e)}"

# ==========================================
# ESTADO DE LA APLICACIÓN (SESSION STATE)
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
if "info_archivos" not in st.session_state: st.session_state.info_archivos = "Ninguno"
# Variables para almacenar archivos generados
if "generated_pptx" not in st.session_state: st.session_state.generated_pptx = None
if "generated_chart" not in st.session_state: st.session_state.generated_chart = None
if "generated_excel" not in st.session_state: st.session_state.generated_excel = None
if "generated_word_clean" not in st.session_state: st.session_state.generated_word_clean = None

# ==========================================
# BARRA LATERAL (CONTROLES)
# ==========================================
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp_val = st.slider("Creatividad (0=Preciso, 1=Libre):", 0.0, 1.0, 0.2)
    
    st.divider()
    
    rol = st.radio("Perfil Activo:", [
        "Vicedecano Académico", 
        "Director de UCI", 
        "Consultor Telesalud", 
        "Profesor Universitario", 
        "Investigador Científico", 
        "Mentor de Trading", 
        "Asistente Personal"
    ])

    prompts_roles = {
        "Vicedecano Académico": "Eres Vicedecano. Riguroso, normativo y formal.",
        "Director de UCI": "Eres Médico Intensivista. Prioriza guías clínicas y seguridad.",
        "Consultor Telesalud": "Eres experto en Salud Digital, interoperabilidad y Leyes.",
        "Profesor Universitario": "Eres docente. Explica con pedagogía y ejemplos.",
        "Investigador Científico": "Eres metodólogo. Prioriza datos y referencias APA.",
        "Mentor de Trading": "Eres Trader Institucional. Analiza estructura de mercado y liquidez.",
        "Asistente Personal": "Eres asistente ejecutivo eficiente y organizado."
    }
    
    st.divider()
    
    # --- ZONA DE HERRAMIENTAS DE SALIDA ---
    st.subheader("🛠️ GENERADOR DE ARCHIVOS")
    
    # 1. WORD LIMPIO (SOLO RESPUESTA)
    if st.button("📄 Word (Solo Respuesta)"):
        if not st.session_state.messages:
            st.error("No hay respuesta para convertir.")
        else:
            last_msg = st.session_state.messages[-1]["content"]
            st.session_state.generated_word_clean = create_clean_docx(last_msg)
            st.success("✅ Documento Creado")
    if st.session_state.generated_word_clean:
        st.download_button("📥 Bajar Documento.docx", st.session_state.generated_word_clean, "documento_ia.docx")

    # 2. POWERPOINT
    if st.button("🗣️ PPTX (Resumen Chat)"):
        if len(st.session_state.messages) < 2: st.error("Necesito historial de chat.")
        else:
            with st.spinner("Diseñando diapositivas..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"Analiza: {hist}. Crea JSON para PPTX (4-6 slides). Formato: [{{'title':'T','content':['A','B']}}]"
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": 0.1})
                    res = mod.generate_content(prompt)
                    clean_json = res.text.replace("```json","").replace("```","").strip()
                    st.session_state.generated_pptx = generate_pptx_from_data(json.loads(clean_json))
                    st.success("✅ PPTX Listo")
                except Exception as e: st.error(f"Error PPTX: {e}")
    if st.session_state.generated_pptx:
        st.download_button("📥 Bajar Presentación.pptx", st.session_state.generated_pptx, "presentacion_ia.pptx")

    # 3. EXCEL (CON REPORTE DE ERRORES)
    if st.button("x ̅  Excel (Tablas/Datos)"):
        if len(st.session_state.messages) < 2: 
            st.error("Faltan datos en el chat.")
        else:
            with st.spinner("Estructurando Excel..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt_excel = f"""
                Analiza el historial: {hist}.
                Si es ENCUESTA: Columnas 'Pregunta', 'Tipo', 'Opciones'.
                Si son DATOS: Columnas correspondientes.
                SALIDA JSON ÚNICA: {{'Hoja1': [{{'ColA':'Val1', 'ColB':'Val2'}}]}}
                """
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": 0.1})
                    res = mod.generate_content(prompt_excel)
                    clean_json = res.text.replace("```json","").replace("```","").strip()
                    st.session_state.generated_excel = generate_excel_from_data(json.loads(clean_json))
                    st.success("✅ Excel Listo")
                except Exception as e: 
                    st.error(f"❌ Error Excel: {e}") # Aquí verá el error real si falla
    if st.session_state.generated_excel:
        st.download_button("📥 Bajar Excel.xlsx", st.session_state.generated_excel, "datos_ia.xlsx")

    # 4. GRÁFICO VISUAL
    if st.button("📊 Generar Gráfico"):
        with st.spinner("Graficando..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Extrae datos numéricos de: {hist}. JSON: {{'title':'T','labels':['A','B'],'datasets':[{{'label':'Serie1','values':[10,20],'type':'bar'}}]}}"
            try:
                genai.configure(api_key=api_key)
                mod = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": 0.1})
                res = mod.generate_content(prompt)
                clean_json = res.text.replace("```json","").replace("```","").strip()
                st.session_state.generated_chart = generate_advanced_chart(json.loads(clean_json))
                st.success("✅ Gráfico Listo (Ver arriba)")
            except Exception as e: st.error(f"No pude graficar: {e}")

    st.divider()
    
    # --- ZONA DE GESTIÓN Y CARGA ---
    st.subheader("📥 FUENTES Y MEMORIA")
    
    # TABS DE CARGA
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Docs", "👁️ Media", "🔴 YT", "🌐 Web"])
    
    with tab1:
        uploaded_docs = st.file_uploader("Subir PDFs/Words", type=['pdf', 'docx'], accept_multiple_files=True)
        if uploaded_docs and st.button(f"Procesar {len(uploaded_docs)} Docs"):
            text_acc = ""
            prog = st.progress(0)
            for i, doc in enumerate(uploaded_docs):
                if doc.type == "application/pdf": text_acc += f"\n--- {doc.name} ---\n{get_pdf_text(doc)}"
                else: text_acc += f"\n--- {doc.name} ---\n{get_docx_text(doc)}"
                prog.progress((i+1)/len(uploaded_docs))
            st.session_state.contexto_texto = text_acc
            st.session_state.info_archivos = f"{len(uploaded_docs)} documentos cargados."
            st.success("✅ Biblioteca Cargada")
    
    with tab2:
        uploaded_media = st.file_uploader("Video/Audio/Img", type=['mp4','mp3','wav','png','jpg'])
        if uploaded_media and api_key and st.button("Subir Media"):
            genai.configure(api_key=api_key)
            with st.spinner("Procesando en Google..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.'+uploaded_media.name.split('.')[-1]) as tf:
                    tf.write(uploaded_media.read()); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
                st.session_state.archivo_multimodal = mfile
                st.success("✅ Multimedia Lista"); os.remove(tpath)
                
    with tab3:
        if st.button("Leer YT") and (u:=st.text_input("Link YT")): 
            st.session_state.contexto_texto = get_youtube_text(u); st.success("✅ YT Leído")
            
    with tab4:
        if st.button("Leer Web") and (w:=st.text_input("Link Web")): 
            st.session_state.contexto_texto = get_web_text(w); st.success("✅ Web Leída")

    st.divider()
    
    # BOTONES DE GESTIÓN
    if st.session_state.messages:
        c1, c2 = st.columns(2)
        c1.download_button("📄 Acta Chat", create_chat_docx(st.session_state.messages), "acta_sesion.docx")
        c2.download_button("🧠 Backup", json.dumps(st.session_state.messages), "memoria.json")
    
    up_mem = st.file_uploader("Restaurar Cerebro", type=['json'])
    if up_mem and st.button("Cargar Memoria"):
        st.session_state.messages = json.load(up_mem); st.rerun()
        
    if st.button("🗑️ Borrar Todo"): st.session_state.clear(); st.rerun()

# ==========================================
# ÁREA PRINCIPAL DE CHAT
# ==========================================
st.title(f"🤖 Agente IkigAI: {rol}")

if not api_key: st.warning("⚠️ Por favor ingrese su API Key en la barra lateral."); st.stop()

# Mostrar Gráfico si existe
if st.session_state.generated_chart:
    st.pyplot(st.session_state.generated_chart)
    if st.button("Cerrar Gráfico"): 
        st.session_state.generated_chart = None; st.rerun()

# Configurar Modelo
genai.configure(api_key=api_key)
try:
    model = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": temp_val})
except Exception as e:
    st.error(f"Error configurando modelo {MODELO_USADO}: {e}")
    st.stop()

# Mostrar Historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# Input de Usuario
if prompt := st.chat_input("Escriba su instrucción aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                # Construcción del Prompt
                hay_contexto = st.session_state.contexto_texto != "" or st.session_state.archivo_multimodal is not None
                modo = "MODO ESTRICTO (Responde SOLO basándote en los archivos adjuntos)." if hay_contexto else "MODO GENERAL (Usa tu conocimiento)."
                
                instruccion_maestra = f"""
                Actúa como {rol}. 
                FECHA: {date.today()}
                CONTEXTO ROL: {prompts_roles[rol]}
                {modo}
                
                ESTILO: Profesional, directo, sin frases robóticas.
                APA 7: Cita fuentes si usas archivos. Webs dinámicas = 'Recuperado el {date.today()}'.
                """
                
                contenido = [instruccion_maestra]
                
                # Adjuntar Archivos
                if st.session_state.contexto_texto:
                    contenido.append(f"\n--- BIBLIOTECA DOCS ---\n{st.session_state.contexto_texto[:500000]}\n--- FIN ---\n")
                
                if st.session_state.archivo_multimodal:
                    contenido.append(st.session_state.archivo_multimodal)
                    contenido.append("(Analiza este archivo multimedia).")
                
                # Adjuntar Historial
                historial_chat = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:]])
                contenido.append(f"\nHISTORIAL CHAT RECIENTE:\n{historial_chat}\n\nNUEVA CONSULTA: {prompt}")

                # Generar
                response = model.generate_content(contenido)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
                
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
