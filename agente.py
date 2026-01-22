import streamlit as st
import google.generativeai as genai
import subprocess
import sys
from datetime import date

# ==========================================
# 1. VERIFICACIÓN DE LIBRERÍA (Nivel Bajo)
# ==========================================
try:
    import google.generativeai as genai
    # Forzamos la versión que soporta tools
    if genai.__version__ < "0.8.3":
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai==0.8.3"])
        st.rerun()
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai==0.8.3"])
    st.rerun()

st.set_page_config(page_title="Test de Conectividad", page_icon="📡")

st.title("📡 Prueba de Fuego: Conexión a Google")

# ==========================================
# CONFIGURACIÓN
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.success(f"✅ API Key Detectada | Librería: v{genai.__version__}")
else:
    api_key = st.text_input("🔑 API Key:", type="password")

if not api_key: st.stop()

genai.configure(api_key=api_key)

# ==========================================
# EL EXPERIMENTO
# ==========================================
st.write("### 🧪 El Experimento")
st.info("Vamos a hacer una pregunta que OBLIGUE a buscar datos recientes.")

pregunta = st.text_input("Pregunta de control:", "Precio actual del Dólar en Colombia hoy")

if st.button("Lanzar Prueba de Conexión"):
    with st.spinner("Conectando con Google Search Grounding..."):
        try:
            # 1. CONFIGURACIÓN EXPLÍCITA DE LA HERRAMIENTA
            tools = [{'google_search': {}}]
            
            # 2. MODELO (Usamos Flash que es el más estable para esto)
            model = genai.GenerativeModel('gemini-1.5-flash', tools=tools)
            
            # 3. GENERACIÓN
            # Forzamos la fecha para que sepa que necesita datos frescos
            prompt = f"Fecha actual: {date.today()}. Responde: {pregunta}"
            response = model.generate_content(prompt)
            
            # 4. LA HORA DE LA VERDAD (INSPECCIÓN DE METADATOS)
            st.divider()
            
            # Verificamos si existe el objeto de metadatos de búsqueda
            tiene_grounding = False
            try:
                if response.candidates[0].grounding_metadata.search_entry_point:
                    tiene_grounding = True
            except:
                pass
            
            # 5. RESULTADO DEL SEMÁFORO
            if tiene_grounding:
                st.success("🟢 CONEXIÓN EXITOSA (ONLINE)")
                st.write("Evidence: Se detectaron 'Grounding Metadata' en la respuesta.")
                with st.expander("Ver Datos Técnicos (Prueba Forense)"):
                    st.json(response.candidates[0].grounding_metadata)
                st.write(f"**Respuesta:** {response.text}")
                
            else:
                st.error("🔴 CONEXIÓN FALLIDA (OFFLINE - MEMORIA INTERNA)")
                st.warning("El modelo respondió, pero NO usó Google Search. Está alucinando o usando memoria base.")
                st.write(f"**Respuesta:** {response.text}")
                
        except Exception as e:
            st.error("💥 ERROR TÉCNICO CRÍTICO")
            st.error(f"El servidor rechazó la conexión: {e}")
            st.write("Diagnóstico: Si sale 'Unknown field', la librería sigue vieja. Si sale '403', la API Key no permite Search.")
