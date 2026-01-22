import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from datetime import date
import time

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Agente V62 (Auto-Model)", page_icon="🗝️", layout="wide")

# ==========================================
# FUNCIONES: BÚSQUEDA SINTÉTICA
# ==========================================
def buscar_en_web(consulta):
    """Busca en DuckDuckGo para obtener datos 2026 sin permisos de Google."""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(consulta, region='co-co', timelimit='y', max_results=4))
            if not resultados: return "No se encontraron datos web."
            
            ctx = "🔴 DATOS DE INTERNET (ÚSALOS):\n"
            for r in resultados:
                ctx += f"- {r['title']}: {r['body']} ({r['href']})\n"
            return ctx
    except Exception as e:
        return f"Error web: {e}"

# ==========================================
# BARRA LATERAL (SELECTOR AUTOMÁTICO)
# ==========================================
with st.sidebar:
    st.header("🗝️ Configuración V62")
    
    # 1. API KEY
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key Detectada")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    # 2. AUTO-SELECCIÓN DE MODELO (LA SOLUCIÓN AL 404)
    modelo_a_usar = None
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Pedimos a Google la lista REAL de modelos disponibles para ESTA clave
            listado = genai.list_models()
            
            opciones_validas = []
            for m in listado:
                if 'generateContent' in m.supported_generation_methods:
                    # Limpiamos el nombre (quitamos 'models/')
                    nombre = m.name.replace("models/", "")
                    opciones_validas.append(nombre)
            
            if opciones_validas:
                # Usamos el primero de la lista (generalmente es gemini-pro o flash)
                modelo_a_usar = st.selectbox("🧠 Modelo Detectado:", opciones_validas, index=0)
                st.success(f"Conectado a: {modelo_a_usar}")
            else:
                st.error("Tu API Key no tiene modelos disponibles.")
        except Exception as e:
            st.error(f"Error de API Key: {e}")

    rol = st.selectbox("Rol:", ["Vicedecano Académico", "Director UCI"])

# ==========================================
# CHAT
# ==========================================
st.title(f"🤖 Agente V62: {rol}")

if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Pregunta: Salario Mínimo 2026"):
    if not api_key: st.warning("Falta API Key"); st.stop()
    if not modelo_a_usar: st.warning("No se detectó ningún modelo válido."); st.stop()
    
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        # 1. BÚSQUEDA WEB (DUCKDUCKGO)
        status = st.status("🕷️ Buscando datos en internet...", expanded=True)
        contexto = buscar_en_web(f"{p} colombia 2026 oficial")
        status.write("Datos obtenidos. Redactando...")
        
        # 2. GENERACIÓN (CON EL MODELO QUE SÍ EXISTE)
        try:
            model = genai.GenerativeModel(modelo_a_usar) # Usamos el que detectamos arriba
            
            prompt = f"""
            FECHA: {date.today()}
            CONTEXTO WEB: {contexto}
            PREGUNTA: {p}
            ROL: {rol}.
            INSTRUCCIÓN: Responde usando el contexto web. Si no hay dato oficial, dilo.
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
            status.update(label="✅ Listo", state="complete", expanded=False)
            
        except Exception as e:
            st.error(f"Error generando: {e}")
