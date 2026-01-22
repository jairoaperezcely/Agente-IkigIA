import streamlit as st
import subprocess
import sys
import time
from datetime import date

# ==========================================
# 🚑 INSTALACIÓN DE MOTORES DE BÚSQUEDA
# ==========================================
try:
    from duckduckgo_search import DDGS
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo-search"])
    from duckduckgo_search import DDGS

try:
    import google.generativeai as genai
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
    import google.generativeai as genai

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agente V60 (Sintético)", page_icon="🕷️", layout="wide")

# ==========================================
# 🧠 CEREBRO: BÚSQUEDA MANUAL (NO NATIVA)
# ==========================================
def buscar_en_web(consulta):
    """Sale a internet manualmente sin pedirle permiso a Google"""
    try:
        with DDGS() as ddgs:
            # Buscamos 5 resultados frescos
            resultados = list(ddgs.text(consulta, region='co-co', timelimit='y', max_results=5))
            
            contexto = "INFORMACIÓN ENCONTRADA EN LA WEB (EN TIEMPO REAL):\n"
            for r in resultados:
                contexto += f"- Título: {r['title']}\n  Resumen: {r['body']}\n  Fuente: {r['href']}\n\n"
            return contexto
    except Exception as e:
        return f"Error buscando en web: {e}"

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("🕷️ Motor V60")
    st.success("Modo: Búsqueda Sintética (Universal)")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    rol = st.selectbox("Rol:", ["Vicedecano Académico", "Director UCI", "Socio Estratégico"])
    
    # Selector de modelo simple (sin tools complejas)
    modelo = st.selectbox("Modelo:", ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-pro-latest"])

# ==========================================
# CHAT
# ==========================================
st.title(f"🤖 Agente V60: {rol}")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Pregunta: Salario Mínimo 2026"):
    if not api_key: st.warning("Falta API Key"); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        status = st.empty()
        status.info("🕷️ Saliendo a buscar en internet...")
        
        # 1. BÚSQUEDA SINTÉTICA (PYTHON HACE EL TRABAJO SUCIO)
        contexto_web = buscar_en_web(p + " salario minimo colombia 2026 decreto")
        
        status.info("🧠 Analizando datos encontrados...")
        
        # 2. GENERACIÓN CON GEMINI (SOLO TEXTO, SIN TOOLS)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(modelo)
        
        prompt_final = f"""
        FECHA DE HOY: {date.today()}
        ROL: {rol}.
        
        CONTEXTO DE INTERNET (ÚSALO PARA RESPONDER):
        {contexto_web}
        
        PREGUNTA DEL USUARIO:
        {p}
        
        INSTRUCCIÓN: Responde la pregunta basándote estrictamente en el CONTEXTO DE INTERNET encontrado.
        Si encontraste cifras, dalas. Si hay decretos, cítalos.
        """
        
        try:
            response = model.generate_content(prompt_final, stream=True)
            
            full_text = ""
            placeholder = st.empty()
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    placeholder.markdown(full_text + "▌")
            placeholder.markdown(full_text)
            
            st.session_state.messages.append({"role": "assistant", "content": full_text})
            status.empty() # Limpiar mensaje de estado
            
        except Exception as e:
            st.error(f"Error: {e}")
