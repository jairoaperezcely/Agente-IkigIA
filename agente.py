import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from datetime import date

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="IkigAI V1.5 - Biblioteca Estratégica", page_icon="🧬", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Configure GOOGLE_API_KEY en st.secrets")
    st.stop()

# --- FUNCIONES DE CARGA ---
def extract_text(files):
    text = ""
    for file in files:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            for page in reader.pages: text += page.extract_text()
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(file)
            text += "\n".join([p.text for p in doc.paragraphs])
    return text

# --- ESTADO DE MEMORIA ---
if "biblioteca" not in st.session_state:
    st.session_state.biblioteca = {rol: "" for rol in [
        "Coach de Alto Desempeño", "Director Centro Telemedicina", 
        "Vicedecano Académico", "Director de UCI", 
        "Consultor Salud Digital", "Profesor Universitario", "Estratega de Trading"
    ]}

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🧬 IkigAI Engine")
    rol_activo = st.selectbox("Perfil Activo:", list(st.session_state.biblioteca.keys()))
    
    st.divider()
    st.subheader(f"📥 Fuentes para {rol_activo}")
    archivos = st.file_uploader("Subir PDF/Docs del rol:", type=['pdf', 'docx'], accept_multiple_files=True)
    
    if st.button("🧠 Alimentar Cerebro"):
        if archivos:
            contenido = extract_text(archivos)
            st.session_state.biblioteca[rol_activo] += f"\n{contenido}"
            st.success(f"Memoria de {rol_activo} actualizada.")

# --- INTERFAZ PRINCIPAL ---
st.header(f"IkigAI en modo: {rol_activo}")

# Muestra si hay documentos cargados para ese rol
if st.session_state.biblioteca[rol_activo]:
    st.caption(f"✅ Este rol tiene {len(st.session_state.biblioteca[rol_activo])} caracteres de contexto específico.")
else:
    st.caption("⚠️ Este rol aún no tiene documentos base cargados.")

prompt = st.chat_input("Instrucción estratégica...")

if prompt:
    with st.chat_message("assistant"):
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # El Prompt Maestro usa el contexto guardado de ese rol específico
        contexto_especifico = st.session_state.biblioteca[rol_activo]
        
        instruccion_sistema = f"""
        Actúa como IkigAI en el rol de {rol_activo}.
        BASE DE CONOCIMIENTO ESPECÍFICA PARA ESTE ROL:
        {contexto_especifico[:800000]}
        
        TU MISIÓN:
        - Responde usando la base de conocimiento adjunta.
        - Sé estratégico, innovador y detecta procrastinación.
        - Estilo ejecutivo, clínico y directo. Sin clichés.
        """
        
        response = model.generate_content([instruccion_sistema, prompt])
        st.markdown(response.text)
