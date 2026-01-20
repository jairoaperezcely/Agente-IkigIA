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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente V9.5 (Masivo & Multimodal)", page_icon="🧬", layout="wide")

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

# --- FUNCIÓN PARA GENERAR WORD (ACTA) ---
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading('Acta de Sesión con IA', 0)
    doc.add_paragraph(f"Fecha de sesión: {date.today().strftime('%d/%m/%Y')}")
    
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "ASISTENTE IA"
        doc.add_heading(role, level=2)
        doc.add_paragraph(msg["content"])
        doc.add_paragraph("---")
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- FUNCIONES WEB Y YOUTUBE ---
def get_youtube_text(video_url):
    try:
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be" in video_url:
            video_id = video_url.split("/")[-1]
        else:
            return "URL inválida."
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['es', 'en'])
        text = " ".join([entry['text'] for entry in transcript])
        return f"TRANSCRIPCIÓN YOUTUBE:\n{text}"
    except:
        return "No se pudo obtener la transcripción."

def get_web_text(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = "\n".join([p.get_text() for p in paragraphs])
        return f"CONTENIDO WEB ({url}):\n{text}"
    except Exception as e:
        return f"Error web: {str(e)}"

# --- LÓGICA DE MEMORIA (ESTADO) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
if "info_archivos" not in st.session_state: st.session_state.info_archivos = "Ninguno"

# --- BARRA LATERAL (CONTROLES) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    
    # 1. CONTROL DE TEMPERATURA
    st.caption("Creatividad (0=Preciso | 1=Libre):")
    temp_val = st.slider("", 0.0, 1.0, 0.2, 0.1)
    
    st.divider()
    
    # 2. SELECCIÓN DE ROL
    rol = st.radio("Perfil Activo:", [
        "Vicedecano Académico", 
        "Director de UCI", 
        "Experto en Telesalud",
        "Investigador Científico",
        "Profesor universitario",
        "Asistente Personal",
        "Mentor de Trading"
    ])
    
    # DICCIONARIO DE ROLES (PROMPTS)
    prompts_roles = {
        "Vicedecano Académico": "Eres un Vicedecano riguroso, ético y normativo. Cita siempre la fuente.",
        "Director de UCI": "Eres Director de UCI. Prioriza seguridad del paciente y guías clínicas.",
        "Mentor de Trading": "Eres Trader Institucional (Smart Money). Analiza liquidez, estructura y riesgo.",
        "Experto en Telesalud": "Eres experto en Salud Digital, interoperabilidad y normativa.",
        "Investigador Científico": "Eres metodólogo. Prioriza validez estadística y bibliografía.",
        "Profesor universitario": "Eres docente socrático. Explica con claridad y analogías.",
        "Asistente Personal": "Eres asistente ejecutivo. Organiza y redacta con formalidad."
    }

    st.divider()
    
    # 3. ZONA DE GUARDADO (SIEMPRE VISIBLE)
    st.subheader("💾 GESTIÓN")
    if len(st.session_state.messages) > 0:
        col1, col2 = st.columns(2)
        docx_file = create_chat_docx(st.session_state.messages)
        col1.download_button("📄 Acta", docx_file, "acta_sesion.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        chat_json = json.dumps(st.session_state.messages)
        col2.download_button("🧠 Backup", chat_json, "memoria.json", "application/json")
    else:
        st.info("Inicia el chat para habilitar guardado.")

    # CARGAR BACKUP
    uploaded_memory = st.file_uploader("Restaurar (.json)", type=['json'])
    if uploaded_memory and st.button("🔄 Cargar Memoria"):
        try:
            st.session_state.messages = json.load(uploaded_memory)
            st.success("¡Memoria restaurada!")
            time.sleep(1)
            st.rerun()
        except:
            st.error("Archivo inválido")

    st.divider()
    
    # 4. CARGA DE ARCHIVOS (MULTIMODAL & MASIVO)
    st.subheader("📥 FUENTES")
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Lote Docs", "👁️ Media", "🔴 YT", "🌐 Web"])
    
    # --- PESTAÑA 1: CARGA MASIVA (PDF/WORD) ---
    with tab1:
        uploaded_docs = st.file_uploader("Subir Múltiples Archivos", 
                                       type=['pdf', 'docx'], 
                                       accept_multiple_files=True)
        
        if uploaded_docs:
            if st.button(f"🧠 Procesar {len(uploaded_docs)} Archivos"):
                texto_acumulado = ""
                barra = st.progress(0)
                with st.spinner("Leyendo biblioteca..."):
                    for i, doc in enumerate(uploaded_docs):
                        try:
                            if doc.type == "application/pdf":
                                contenido = get_pdf_text(doc)
                            else:
                                contenido = get_docx_text(doc)
                            texto_acumulado += f"\n--- INICIO ARCHIVO: {doc.name} ---\n{contenido}\n--- FIN ARCHIVO ---\n"
                        except:
                            st.error(f"Error en {doc.name}")
                        barra.progress((i + 1) / len(uploaded_docs))
                
                st.session_state.contexto_texto = texto_acumulado
                st.session_state.info_archivos = f"{len(uploaded_docs)} archivos cargados."
                st.success("✅ ¡Biblioteca cargada a la memoria!")

        if st.session_state.info_archivos != "Ninguno":
            st.caption(f"En memoria: {st.session_state.info_archivos}")

    # --- PESTAÑA 2: MULTIMEDIA (VIDEO, IMAGEN, AUDIO) ---
    with tab2:
        uploaded_media = st.file_uploader("Video/Foto/Audio", type=['mp4', 'mov', 'png', 'jpg', 'jpeg', 'mp3', 'wav', 'm4a'])
        if uploaded_media and api_key and st.button("Subir Media"):
            genai.configure(api_key=api_key)
            with st.spinner(f"Procesando {uploaded_media.type}..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_media.name.split('.')[-1]) as tmp_file:
                    tmp_file.write(uploaded_media.read())
                    tmp_path = tmp_file.name
                
                media_file = genai.upload_file(path=tmp_path)
                
                while media_file.state.name == "PROCESSING":
                    time.sleep(2)
                    media_file = genai.get_file(media_file.name)
                
                st.session_state.archivo_multimodal = media_file
                st.success("✅ Archivo multimedia listo")
                os.remove(tmp_path)

    # --- PESTAÑA 3: YOUTUBE ---
    with tab3:
        if st.button("Leer YT") and (yt_url := st.text_input("Link YT")):
            st.session_state.contexto_texto = get_youtube_text(yt_url)
            st.success("✅ YT Cargado")
            
    # --- PESTAÑA 4: WEB ---
    with tab4:
        if st.button("Leer Web") and (web_url := st.text_input("Link Web")):
            st.session_state.contexto_texto = get_web_text(web_url)
            st.success("✅ Web Cargada")

    if st.button("🗑️ Nueva Sesión"):
        st.session_state.messages = []
        st.session_state.contexto_texto = ""
        st.session_state.archivo_multimodal = None
        st.session_state.info_archivos = "Ninguno"
        st.rerun()

# --- CHAT PRINCIPAL ---
st.title(f"🤖 Agente: {rol}")

if not api_key:
    st.warning("⚠️ Ingrese API Key.")
    st.stop()

genai.configure(api_key=api_key)
generation_config = {"temperature": temp_val}

try:
    # Usamos Flash por velocidad y capacidad de contexto masivo
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)
except Exception as e:
    st.error(f"Error Gemini: {e}")
    st.stop()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escriba su instrucción..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                contenido = []
                fecha_hoy = date.today().strftime("%d de %B de %Y")
                
                # --- PROMPT MAESTRO (APA 7 + ANTI-ROBOT) ---
                instruccion = f"""
                Actúa como {rol}.
                FECHA DE HOY: {fecha_hoy}
                CONTEXTO: {prompts_roles[rol]}
                
                REGLAS DE ESTILO (ANTI-ROBOT):
                1. Escribe natural. PROHIBIDO usar: "cabe destacar", "en conclusión", "juega un papel crucial", "tapiz", "sinergia", "desbloquear potencial".
                2. Sé directo y profesional.
                
                REGLAS DE CITACIÓN (APA 7a Edición):
                1. Basa tus respuestas EXCLUSIVAMENTE en los archivos adjuntos.
                2. SI TIENE DOI: https://doi.org/...
                3. FUENTES ESTABLES (PDFs, Artículos): Cita (Autor, Año). NO uses "Recuperado de".
                4. FUENTES DINÁMICAS (Webs vivas): Usa "Recuperado el {fecha_hoy} de [URL]".
                5. Si no está en el documento, di: "No se menciona en el texto".
                """
                
                # Inyectar Texto Acumulado
                if st.session_state.contexto_texto:
                    instruccion += f"\n\n--- BIBLIOTECA DE ARCHIVOS ---\n{st.session_state.contexto_texto[:800000]}\n--- FIN BIBLIOTECA ---\n"
                
                # Inyectar Multimedia
                if st.session_state.archivo_multimodal:
                    contenido.append(st.session_state.archivo_multimodal)
                    instruccion += " (Analiza el archivo multimedia adjunto)."

                # Historial
                historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
                instruccion += f"\n\nHISTORIAL:\n{historial}\n\nSOLICITUD: {prompt}"

                contenido.append(instruccion)
                
                response = model.generate_content(contenido)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")

