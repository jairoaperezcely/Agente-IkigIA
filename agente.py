import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Agente Médico IA - V3.0", page_icon="🧬", layout="wide")

# --- BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # 1. API KEY
    api_key = st.text_input("Ingrese su API Key:", type="password")
    
    st.divider()

    # 2. SELECCIÓN DE ROL
    st.subheader("🎭 Seleccione el Rol")
    rol = st.radio(
        "¿Quién soy hoy?",
        ["Vicedecano Académico", "Director de UCI", "Mentor de Trading", "Experto en Telesalud", "Asistente General"]
    )

    st.divider()

    # 3. CARGA DE ARCHIVOS
    st.subheader("📂 Documentos")
    uploaded_file = st.file_uploader("Subir PDF o Word (Opcional)", type=['pdf', 'docx'])
    
    # Botón para limpiar historial
    if st.button("🗑️ Borrar Chat y Empezar de Nuevo"):
        st.session_state.messages = []
        st.session_state.doc_text = ""
        st.rerun()

# --- FUNCIONES DE LECTURA ---
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- LÓGICA DE MEMORIA (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "doc_text" not in st.session_state:
    st.session_state.doc_text = ""

# Procesar archivo si se sube uno nuevo
if uploaded_file:
    # Solo leer si es diferente al anterior para no recargar
    file_key = f"file_{uploaded_file.name}"
    if "current_file" not in st.session_state or st.session_state.current_file != uploaded_file.name:
        with st.spinner("Leyendo documento..."):
            if uploaded_file.type == "application/pdf":
                st.session_state.doc_text = get_pdf_text(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                st.session_state.doc_text = get_docx_text(uploaded_file)
            st.session_state.current_file = uploaded_file.name
        st.success("✅ Documento cargado y listo para chatear.")

# --- INTERFAZ PRINCIPAL ---
st.title(f"🤖 Agente Activo: {rol}")

# Mostrar advertencia si falta la API Key
if not api_key:
    st.warning("⚠️ Por favor ingrese su API Key en la barra lateral para comenzar.")
    st.stop()

# Configurar el modelo
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# 1. MOSTRAR HISTORIAL DE CHAT
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 2. CAPTURAR NUEVA PREGUNTA (CHAT INPUT)
if prompt := st.chat_input("Escriba su instrucción aquí..."):
    # Guardar y mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. CONSTRUIR EL CONTEXTO PARA LA IA
    # Aquí unimos: Rol + Documento + Historial + Pregunta Nueva
    
    contexto_doc = ""
    if st.session_state.doc_text:
        contexto_doc = f"\n\nCONTEXTO DEL DOCUMENTO ADJUNTO:\n{st.session_state.doc_text[:30000]}...\n(Fin del documento)\n"

    instruccion_sistema = f"""
    Actúa como un experto en el rol de: {rol}.
    
    {contexto_doc}
    
    Tu objetivo es responder a la última pregunta del usuario basándote en el documento (si existe) y manteniendo la coherencia de la conversación.
    """

    # Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                # Enviamos el historial reciente para que tenga memoria
                chat_history = []
                # Convertimos el historial de Streamlit al formato de Gemini
                for msg in st.session_state.messages[:-1]: # Todos menos el último que acabamos de poner
                    role = "user" if msg["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [msg["content"]]})
                
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(instruccion_sistema + "\n\nPregunta actual: " + prompt)
                
                st.markdown(response.text)
                
                # Guardar respuesta en historial
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
