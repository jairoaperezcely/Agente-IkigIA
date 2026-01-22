import streamlit as st
import subprocess
import sys
import google.generativeai as genai
from datetime import date

# ==========================================
# 🚑 ZONA DE SEGURIDAD (Update Librería)
# ==========================================
try:
    import google.generativeai as genai
    if genai.__version__ < "0.8.3":
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai==0.8.3"])
        st.rerun()
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai==0.8.3"])
    st.rerun()

st.set_page_config(page_title="Agente V58 (Scanner)", page_icon="📡", layout="wide")

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
Eres un Asistente Experto en 2026.
TU OBJETIVO: Buscar información actual (Salarios, leyes, noticias) usando Google Search.
SI NO PUEDES BUSCAR: Dilo honestamente ("No tengo conexión"), no inventes que no existe el dato.
"""

# ==========================================
# BARRA LATERAL (ESCÁNER DE MODELOS)
# ==========================================
with st.sidebar:
    st.header("📡 Escáner de Modelos")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key Detectada")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    if not api_key:
        st.warning("Ingrese API Key para escanear.")
        st.stop()

    genai.configure(api_key=api_key)

    # --- ESCANEO REAL ---
    st.write("🔍 Buscando modelos compatibles...")
    opciones_modelos = []
    try:
        for m in genai.list_models():
            # Filtramos solo los que sirven para chatear
            if 'generateContent' in m.supported_generation_methods:
                # Limpiamos el nombre (quitamos 'models/')
                nombre_limpio = m.name.replace("models/", "")
                opciones_modelos.append(nombre_limpio)
    except Exception as e:
        st.error(f"Error escaneando: {e}")

    # SELECTOR
    if opciones_modelos:
        modelo_seleccionado = st.selectbox("🧠 Selecciona tu Modelo:", opciones_modelos, index=0)
        st.caption(f"Usando: `{modelo_seleccionado}`")
    else:
        st.error("No se encontraron modelos. Verifique su API Key.")
        st.stop()
        
    rol = st.selectbox("Rol:", ["Socio Estratégico", "Vicedecano"])

# ==========================================
# CHAT CON CONEXIÓN REAL
# ==========================================
st.title(f"🤖 Agente V58: {rol}")
st.caption(f"Conectado vía: {modelo_seleccionado}")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input(f"Pregunta al {modelo_seleccionado}..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        try:
            # 1. Configurar Herramienta de Búsqueda
            tools = [{'google_search': {}}]
            
            # 2. Iniciar Modelo Seleccionado
            model = genai.GenerativeModel(
                model_name=modelo_seleccionado, 
                tools=tools, 
                system_instruction=MEMORIA_MAESTRA
            )
            
            # 3. Prompt Forzoso
            prompt_full = f"FECHA HOY: {date.today()}. Consulta: {p}. (OBLIGATORIO: USA LA HERRAMIENTA GOOGLE SEARCH PARA RESPONDER)."
            
            # 4. Generar
            response = model.generate_content(prompt_full, stream=True)
            
            full_text = ""
            placeholder = st.empty()
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    placeholder.markdown(full_text + "▌")
            placeholder.markdown(full_text)
            st.session_state.messages.append({"role": "assistant", "content": full_text})
            
        except Exception as e:
            st.error("💥 Error de Conexión:")
            st.code(str(e))
            st.warning("Prueba seleccionando OTRO modelo en la barra lateral.")
