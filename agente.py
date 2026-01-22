import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from datetime import date
import time

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agente V66 (Bypass)", page_icon="🌐", layout="wide")

# ==========================================
# CEREBRO DE BÚSQUEDA (EXTERNO)
# ==========================================
def buscar_en_web(consulta):
    """
    Busca en internet usando DuckDuckGo. 
    Esto funciona INDEPENDIENTE de la versión de la librería de Google.
    """
    try:
        with DDGS() as ddgs:
            # Buscamos 4 resultados de Colombia
            resultados = list(ddgs.text(consulta, region='co-co', timelimit='y', max_results=4))
            
            if not resultados:
                return "No se encontraron resultados."
            
            texto = "DATOS ENCONTRADOS EN LA WEB (TIEMPO REAL):\n"
            for r in resultados:
                texto += f"- {r['title']}: {r['body']} (Fuente: {r['href']})\n"
            return texto
    except Exception as e:
        return f"Error en búsqueda externa: {e}"

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("🌐 Conexión V66")
    st.success("Modo: Búsqueda Externa (DuckDuckGo)")
    
    # Verificación de API Key
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    rol = st.selectbox("Rol:", ["Vicedecano Académico", "Director UCI", "Socio Estratégico"])

# ==========================================
# CHAT
# ==========================================
st.title(f"🤖 Agente V66: {rol}")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Ej: Salario mínimo Colombia 2026"):
    if not api_key: st.warning("Falta API Key"); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        # 1. BÚSQUEDA (El código Python hace el trabajo sucio)
        status = st.status("🕷️ Buscando en internet (DuckDuckGo)...", expanded=True)
        contexto = buscar_en_web(f"{p} colombia 2026 oficial")
        status.write("Datos obtenidos. Analizando...")
        
        # 2. PENSAMIENTO (Gemini solo procesa el texto, no busca)
        try:
            genai.configure(api_key=api_key)
            # Usamos el modelo estándar sin 'tools', así evitamos el error "Unknown field"
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            FECHA ACTUAL: {date.today()}
            ROL: {rol}
            
            INFORMACIÓN DE INTERNET (ÚSALA OBLIGATORIAMENTE):
            {contexto}
            
            PREGUNTA DEL USUARIO:
            {p}
            
            INSTRUCCIÓN: Responde usando la información de internet.
            """
            
            response = model.generate_content(prompt, stream=True)
            
            full_text = ""
            placeholder = st.empty()
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    placeholder.markdown(full_text + "▌")
            placeholder.markdown(full_text)
            
            st.session_state.messages.append({"role": "assistant", "content": full_text})
            status.update(label="✅ Respuesta Generada", state="complete", expanded=False)
            
        except Exception as e:
            st.error(f"Error generando respuesta: {e}")
